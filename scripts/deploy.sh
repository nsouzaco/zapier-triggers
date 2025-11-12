#!/bin/bash
# Deployment script for Zapier Triggers API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DEPLOYMENT_TYPE="lambda"
ENVIRONMENT="dev"
REGION="us-east-1"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            DEPLOYMENT_TYPE="$2"
            shift 2
            ;;
        --env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}🚀 Deploying Zapier Triggers API${NC}"
echo -e "Deployment Type: ${YELLOW}${DEPLOYMENT_TYPE}${NC}"
echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "Region: ${YELLOW}${REGION}${NC}"
echo ""

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install AWS CLI.${NC}"
    exit 1
fi

if [ "$DEPLOYMENT_TYPE" = "lambda" ]; then
    if ! command -v sam &> /dev/null; then
        echo -e "${RED}❌ SAM CLI not found. Please install SAM CLI.${NC}"
        echo "Install: brew install aws-sam-cli"
        exit 1
    fi
fi

if [ "$DEPLOYMENT_TYPE" = "docker" ]; then
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
        exit 1
    fi
fi

# Get Terraform outputs
echo -e "${YELLOW}📋 Getting Terraform outputs...${NC}"
cd terraform
TERRAFORM_OUTPUTS=$(terraform output -json)
cd ..

# Extract values
SQS_QUEUE_URL=$(echo $TERRAFORM_OUTPUTS | jq -r '.sqs_event_queue_url.value')
SQS_DLQ_URL=$(echo $TERRAFORM_OUTPUTS | jq -r '.sqs_dlq_url.value')
DYNAMODB_TABLE=$(echo $TERRAFORM_OUTPUTS | jq -r '.dynamodb_table_name.value')
REDIS_ENDPOINT=$(echo $TERRAFORM_OUTPUTS | jq -r '.redis_endpoint.value')
RDS_ENDPOINT=$(echo $TERRAFORM_OUTPUTS | jq -r '.rds_endpoint.value')
API_ROLE_ARN=$(echo $TERRAFORM_OUTPUTS | jq -r '.api_role_arn.value')
WORKER_ROLE_ARN=$(echo $TERRAFORM_OUTPUTS | jq -r '.worker_role_arn.value')

# Get RDS password from terraform.tfvars
RDS_PASSWORD=$(grep rds_password terraform/terraform.tfvars | cut -d'"' -f2)

if [ -z "$SQS_QUEUE_URL" ] || [ "$SQS_QUEUE_URL" = "null" ]; then
    echo -e "${RED}❌ Failed to get Terraform outputs. Make sure infrastructure is deployed.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Terraform outputs retrieved${NC}"
echo ""

# Deploy based on type
if [ "$DEPLOYMENT_TYPE" = "lambda" ]; then
    echo -e "${YELLOW}🐳 Building Docker images for Lambda...${NC}"
    
    # Get AWS account ID
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    API_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/zapier-triggers-api-${ENVIRONMENT}-api"
    WORKER_REPO="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/zapier-triggers-api-${ENVIRONMENT}-worker"
    
    # Create ECR repositories if they don't exist
    echo -e "${YELLOW}📦 Creating ECR repositories...${NC}"
    aws ecr describe-repositories --repository-names zapier-triggers-api-${ENVIRONMENT}-api --region $REGION 2>&1 | grep -q "RepositoryNotFoundException" && \
        aws ecr create-repository --repository-name zapier-triggers-api-${ENVIRONMENT}-api --region $REGION > /dev/null
    aws ecr describe-repositories --repository-names zapier-triggers-api-${ENVIRONMENT}-worker --region $REGION 2>&1 | grep -q "RepositoryNotFoundException" && \
        aws ecr create-repository --repository-name zapier-triggers-api-${ENVIRONMENT}-worker --region $REGION > /dev/null
    
    # Login to ECR
    echo -e "${YELLOW}🔐 Logging in to ECR...${NC}"
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com
    
    # NOTE: API function now uses zip deployment with layers
    # Use scripts/deploy-zip.sh instead for API deployment
    echo -e "${YELLOW}⚠️  API function now uses zip deployment.${NC}"
    echo -e "${YELLOW}   Use './scripts/deploy-zip.sh' for API deployment.${NC}"
    echo -e "${YELLOW}   Skipping API container image build...${NC}"
    
    # Build and push Worker image (Lambda requires linux/amd64, use legacy Docker format)
    echo -e "${YELLOW}🏗️  Building Worker image (linux/amd64)...${NC}"
    DOCKER_BUILDKIT=0 docker build --platform linux/amd64 -f Dockerfile.worker -t zapier-triggers-api-${ENVIRONMENT}-worker:latest .
    docker tag zapier-triggers-api-${ENVIRONMENT}-worker:latest ${WORKER_REPO}:latest
    echo -e "${YELLOW}📤 Pushing Worker image...${NC}"
    DOCKER_BUILDKIT=0 docker push ${WORKER_REPO}:latest
    
    # Build and deploy with SAM
    echo -e "${YELLOW}🚀 Building SAM application...${NC}"
    sam build \
        --template template.yaml \
        --parameter-overrides \
            ProjectName=zapier-triggers-api \
            Environment=$ENVIRONMENT \
            SqsEventQueueUrl=$SQS_QUEUE_URL \
            SqsDlqUrl=$SQS_DLQ_URL \
            DynamoDBTableName=$DYNAMODB_TABLE \
            RedisEndpoint=$REDIS_ENDPOINT \
            RdsEndpoint=$RDS_ENDPOINT \
            RdsPassword=$RDS_PASSWORD \
            ApiRoleArn=$API_ROLE_ARN \
            WorkerRoleArn=$WORKER_ROLE_ARN
    
    echo -e "${YELLOW}🚀 Deploying to AWS...${NC}"
    sam deploy \
        --stack-name zapier-triggers-api-$ENVIRONMENT \
        --capabilities CAPABILITY_IAM \
        --region $REGION \
        --no-confirm-changeset \
        --no-fail-on-empty-changeset \
        --resolve-s3 \
        --resolve-image-repos \
        --parameter-overrides \
            ProjectName=zapier-triggers-api \
            Environment=$ENVIRONMENT \
            SqsEventQueueUrl=$SQS_QUEUE_URL \
            SqsDlqUrl=$SQS_DLQ_URL \
            DynamoDBTableName=$DYNAMODB_TABLE \
            RedisEndpoint=$REDIS_ENDPOINT \
            RdsEndpoint=$RDS_ENDPOINT \
            RdsPassword=$RDS_PASSWORD \
            ApiRoleArn=$API_ROLE_ARN \
            WorkerRoleArn=$WORKER_ROLE_ARN
    
    echo -e "${GREEN}✅ Lambda deployment complete!${NC}"
    
    # Get API URL
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name zapier-triggers-api-$ENVIRONMENT \
        --region $REGION \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
        --output text)
    
    echo -e "${GREEN}🌐 API URL: ${API_URL}${NC}"
    
elif [ "$DEPLOYMENT_TYPE" = "docker" ]; then
    echo -e "${YELLOW}🐳 Building Docker image...${NC}"
    
    # Build image
    IMAGE_NAME="zapier-triggers-api:$ENVIRONMENT"
    docker build -t $IMAGE_NAME .
    
    echo -e "${GREEN}✅ Docker image built: ${IMAGE_NAME}${NC}"
    echo ""
    echo -e "${YELLOW}📝 To deploy to ECS or App Runner:${NC}"
    echo "1. Push image to ECR:"
    echo "   aws ecr create-repository --repository-name zapier-triggers-api --region $REGION"
    echo "   docker tag $IMAGE_NAME <account-id>.dkr.ecr.$REGION.amazonaws.com/zapier-triggers-api:$ENVIRONMENT"
    echo "   aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin <account-id>.dkr.ecr.$REGION.amazonaws.com"
    echo "   docker push <account-id>.dkr.ecr.$REGION.amazonaws.com/zapier-triggers-api:$ENVIRONMENT"
    echo ""
    echo "2. Create ECS task definition or App Runner service with environment variables:"
    echo "   SQS_EVENT_QUEUE_URL=$SQS_QUEUE_URL"
    echo "   DYNAMODB_TABLE_NAME=$DYNAMODB_TABLE"
    echo "   REDIS_ENDPOINT=$REDIS_ENDPOINT"
    echo "   RDS_ENDPOINT=$RDS_ENDPOINT"
    echo "   RDS_PASSWORD=<password>"
    
else
    echo -e "${RED}❌ Unknown deployment type: $DEPLOYMENT_TYPE${NC}"
    echo "Supported types: lambda, docker"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"

