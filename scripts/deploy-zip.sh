#!/bin/bash
# Deployment script for Zip-based Lambda deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="dev"
REGION="us-east-1"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
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

echo -e "${GREEN}🚀 Deploying Zapier Triggers API (Zip + Layers)${NC}"
echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "Region: ${YELLOW}${REGION}${NC}"
echo ""

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install AWS CLI.${NC}"
    exit 1
fi

if ! command -v sam &> /dev/null; then
    echo -e "${RED}❌ SAM CLI not found. Please install SAM CLI.${NC}"
    echo "Install: brew install aws-sam-cli"
    exit 1
fi

# Build Lambda Layer (using Docker for cross-platform compatibility)
echo -e "${YELLOW}📦 Building Lambda Layer...${NC}"
if command -v docker &> /dev/null; then
    ./scripts/build-lambda-layer-docker.sh
else
    echo -e "${YELLOW}Docker not found, trying local build...${NC}"
    ./scripts/build-lambda-layer.sh
fi

# Build Function Zip
echo -e "${YELLOW}📦 Building Function Zip...${NC}"
./scripts/build-function-zip.sh

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
VPC_ID=$(echo $TERRAFORM_OUTPUTS | jq -r '.vpc_id.value')
SUBNET_IDS=$(echo $TERRAFORM_OUTPUTS | jq -r '.subnet_ids.value | join(",")')
LAMBDA_SG_ID=$(echo $TERRAFORM_OUTPUTS | jq -r '.lambda_security_group_id.value')

# Get RDS password from terraform.tfvars
RDS_PASSWORD=$(grep rds_password terraform/terraform.tfvars | cut -d'"' -f2)

if [ -z "$SQS_QUEUE_URL" ] || [ "$SQS_QUEUE_URL" = "null" ]; then
    echo -e "${RED}❌ Failed to get Terraform outputs. Make sure infrastructure is deployed.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Terraform outputs retrieved${NC}"
echo ""

# Build and deploy with SAM
echo -e "${YELLOW}🚀 Building SAM application...${NC}"
sam build \
    --template template.zip.yaml \
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
        # VPC parameters removed - Lambda functions no longer in VPC
        # VpcId=$VPC_ID \
        # SubnetIds=$SUBNET_IDS \
        # LambdaSecurityGroupId=$LAMBDA_SG_ID

echo -e "${YELLOW}🚀 Deploying to AWS...${NC}"
sam deploy \
    --stack-name zapier-triggers-api-$ENVIRONMENT \
    --capabilities CAPABILITY_IAM \
    --region $REGION \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --resolve-s3 \
    --resolve-image-repos \
    --template-file template.zip.yaml \
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
        # VPC parameters removed - Lambda functions no longer in VPC
        # VpcId=$VPC_ID \
        # SubnetIds=$SUBNET_IDS \
        # LambdaSecurityGroupId=$LAMBDA_SG_ID

    echo -e "${GREEN}✅ Lambda deployment complete!${NC}"

# Get API URL
API_URL=$(aws cloudformation describe-stacks \
    --stack-name zapier-triggers-api-$ENVIRONMENT \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
    --output text)

echo -e "${GREEN}🌐 API URL: ${API_URL}${NC}"
echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"

