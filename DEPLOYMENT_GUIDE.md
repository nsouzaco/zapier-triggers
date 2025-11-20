# Deployment Guide: Zapier Triggers API

## Current Deployment Status

### API Location
- **API URL**: `https://c259qcghe5.execute-api.us-east-1.amazonaws.com/Prod`
- **Stack Name**: `zapier-triggers-api-dev`
- **Region**: `us-east-1`
- **Deployment Type**: AWS Lambda (serverless)
- **Status**: ✅ Deployed and active

### CloudFormation Stacks
The following stacks are currently deployed:
- `zapier-triggers-api-dev` (main development stack)
- `zapier-triggers-api-prod-mlx`
- `zapier-triggers-api-dev-mlx`
- `alexho-zapier-triggers-api-staging`

---

## How to Redeploy the API

### Quick Redeploy (Recommended)

**For API Lambda (zip deployment):**
```bash
./scripts/deploy-zip.sh
```

This script will:
1. Build Lambda Layer (dependencies)
2. Build Function Zip (application code)
3. Get Terraform outputs (infrastructure config)
4. Deploy via SAM to AWS Lambda
5. Show the API URL when complete

**Options:**
```bash
# Deploy to dev environment (default)
./scripts/deploy-zip.sh

# Deploy to specific environment
./scripts/deploy-zip.sh --env dev

# Deploy to specific region
./scripts/deploy-zip.sh --region us-east-1
```

### Step-by-Step Manual Redeploy

#### 1. **Build Lambda Layer (Dependencies)**
```bash
# Using Docker (recommended for cross-platform)
./scripts/build-lambda-layer-docker.sh

# Or using local build
./scripts/build-lambda-layer.sh
```

#### 2. **Build Function Zip (Application Code)**
```bash
./scripts/build-function-zip.sh
```

#### 3. **Get Infrastructure Configuration**
```bash
# Get Terraform outputs (SQS, DynamoDB, RDS, Redis endpoints)
cd terraform
terraform output -json
cd ..
```

#### 4. **Deploy with SAM**
```bash
sam build --template template.zip.yaml \
  --parameter-overrides \
    ProjectName=zapier-triggers-api \
    Environment=dev \
    SqsEventQueueUrl=<from-terraform> \
    SqsDlqUrl=<from-terraform> \
    DynamoDBTableName=<from-terraform> \
    RedisEndpoint=<from-terraform> \
    RdsEndpoint=<from-terraform> \
    RdsPassword=<from-terraform> \
    ResendApiKey=<from-env> \
    ApiRoleArn=<from-terraform> \
    WorkerRoleArn=<from-terraform>

sam deploy \
  --stack-name zapier-triggers-api-dev \
  --capabilities CAPABILITY_IAM \
  --region us-east-1 \
  --template-file template.zip.yaml \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset \
  --resolve-s3
```

**Or use the automated script:**
```bash
./scripts/deploy-zip.sh
```

---

## Deployment Architecture

### Components Deployed

1. **API Lambda Function**
   - **Function Name**: `zapier-triggers-api-dev-api`
   - **Handler**: `lambda_handler_zip.handler`
   - **Runtime**: Python 3.11
   - **Memory**: 1024 MB
   - **Timeout**: 60 seconds
   - **Deployment**: Zip file + Lambda Layer

2. **Worker Lambda Function**
   - **Function Name**: `zapier-triggers-api-dev-worker`
   - **Handler**: `lambda_worker_zip.handler`
   - **Runtime**: Python 3.11
   - **Memory**: 1024 MB
   - **Timeout**: 300 seconds (5 minutes)
   - **Trigger**: SQS EventSourceMapping
   - **Deployment**: Container image (ECR)

3. **API Gateway**
   - **Type**: REST API
   - **Integration**: Lambda Proxy
   - **Routes**: `/{proxy+}` and `/`

4. **Lambda Layer**
   - **Layer Name**: `zapier-triggers-api-dev-dependencies`
   - **Content**: Python dependencies (from `requirements.txt`)

---

## Prerequisites

### Required Tools
- **AWS CLI**: `aws --version` (must be configured)
- **SAM CLI**: `sam --version` (for Lambda deployment)
- **Terraform**: `terraform --version` (for infrastructure)
- **Docker**: `docker --version` (for building layers)
- **jq**: `jq --version` (for JSON parsing)

### AWS Configuration
```bash
# Configure AWS credentials
aws configure

# Verify access
aws sts get-caller-identity
```

### Required Environment Variables
The deployment script reads from:
- **Terraform outputs**: Infrastructure endpoints (SQS, DynamoDB, RDS, Redis)
- **`.env` file**: `RESEND_API_KEY` (optional, for email notifications)
- **`terraform/terraform.tfvars`**: `rds_password`

---

## What Gets Deployed

### Files Included in Deployment

**Lambda Layer (Dependencies):**
- All packages from `requirements.txt`
- Built into `dependencies-layer.zip`

**Function Zip (Application Code):**
- `lambda_handler_zip.py` (API entry point)
- `lambda_worker_zip.py` (Worker entry point)
- `app/` directory (all application code)
- Excludes: `tests/`, `venv/`, `__pycache__/`, etc.

### Infrastructure (via Terraform)
- VPC, Subnets, Security Groups
- RDS PostgreSQL
- DynamoDB Table
- SQS Queues
- ElastiCache Redis
- IAM Roles
- API Gateway (created by SAM)

---

## Deployment Process

### Automated Deployment Flow

```
1. Build Lambda Layer
   ↓
2. Build Function Zip
   ↓
3. Get Terraform Outputs
   ↓
4. Build SAM Application
   ↓
5. Deploy to AWS (CloudFormation)
   ↓
6. Update Lambda Functions
   ↓
7. Show API URL
```

### What Happens During Deployment

1. **Build Phase**:
   - Creates `dependencies-layer.zip` with Python packages
   - Creates `function.zip` with application code
   - Validates SAM template

2. **Deploy Phase**:
   - Uploads zip files to S3 (via SAM)
   - Creates/updates CloudFormation stack
   - Updates Lambda function code
   - Updates Lambda Layer version
   - Configures API Gateway routes
   - Sets environment variables

3. **Verification**:
   - Checks stack status
   - Retrieves API Gateway URL
   - Displays deployment summary

---

## Common Deployment Scenarios

### Scenario 1: Deploy After Code Changes

```bash
# Make your code changes
git add .
git commit -m "Your changes"

# Redeploy
./scripts/deploy-zip.sh
```

### Scenario 2: Deploy After Infrastructure Changes

```bash
# Update infrastructure first
cd terraform
terraform apply
cd ..

# Then redeploy application
./scripts/deploy-zip.sh
```

### Scenario 3: Deploy to Different Environment

```bash
# Deploy to production (if configured)
./scripts/deploy-zip.sh --env prod --region us-east-1
```

### Scenario 4: Update Only Dependencies

```bash
# Rebuild layer
./scripts/build-lambda-layer-docker.sh

# Redeploy
./scripts/deploy-zip.sh
```

---

## Troubleshooting Deployment

### Error: "Terraform outputs not available"
**Solution**: Deploy infrastructure first
```bash
cd terraform
terraform init
terraform apply
cd ..
```

### Error: "SAM CLI not found"
**Solution**: Install SAM CLI
```bash
# macOS
brew install aws-sam-cli

# Or via pip
pip install aws-sam-cli
```

### Error: "Failed to get Terraform outputs"
**Solution**: Check Terraform state
```bash
cd terraform
terraform output
# If empty, run: terraform apply
```

### Error: "Access Denied" or "Invalid credentials"
**Solution**: Configure AWS credentials
```bash
aws configure
# Or set environment variables:
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
```

### Error: "Stack not found"
**Solution**: Check stack name and region
```bash
aws cloudformation list-stacks \
  --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE \
  --region us-east-1
```

### Error: "Function code too large"
**Solution**: Ensure Lambda Layer is built correctly
```bash
# Rebuild layer
./scripts/build-lambda-layer-docker.sh

# Check zip sizes
ls -lh dependencies-layer.zip function.zip
```

---

## Verifying Deployment

### Check Deployment Status

```bash
# Check CloudFormation stack
aws cloudformation describe-stacks \
  --stack-name zapier-triggers-api-dev \
  --region us-east-1

# Check Lambda functions
aws lambda list-functions \
  --region us-east-1 \
  --query 'Functions[?contains(FunctionName, `zapier-triggers-api-dev`)].FunctionName'
```

### Test API Endpoint

```bash
# Get API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name zapier-triggers-api-dev \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

# Test health endpoint
curl "${API_URL}/health"
```

### Check Lambda Logs

```bash
# API Lambda logs
aws logs tail /aws/lambda/zapier-triggers-api-dev-api --follow

# Worker Lambda logs
aws logs tail /aws/lambda/zapier-triggers-api-dev-worker --follow
```

---

## Deployment Checklist

Before deploying:
- [ ] Code changes committed
- [ ] Tests passing locally
- [ ] AWS credentials configured
- [ ] Terraform infrastructure deployed
- [ ] Environment variables set (`.env` file)
- [ ] RDS password in `terraform.tfvars`

After deploying:
- [ ] Verify API URL is accessible
- [ ] Test health endpoint
- [ ] Test event submission
- [ ] Check CloudWatch logs for errors
- [ ] Verify Lambda functions updated
- [ ] Test worker processing (submit event, check logs)

---

## Current API Endpoints

**Base URL**: `https://c259qcghe5.execute-api.us-east-1.amazonaws.com/Prod`

**Available Endpoints:**
- `GET /health` - Health check
- `GET /` - API information
- `POST /api/v1/events` - Submit events
- `GET /api/v1/inbox` - Retrieve events
- `DELETE /api/v1/inbox/{event_id}` - Delete event
- `POST /admin/test-customer` - Create test customer (dev only)
- `POST /admin/test-subscription` - Create test subscription (dev only)

---

## Quick Reference

### Get Current API URL
```bash
aws cloudformation describe-stacks \
  --stack-name zapier-triggers-api-dev \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text
```

### Redeploy Everything
```bash
# 1. Update infrastructure (if needed)
cd terraform && terraform apply && cd ..

# 2. Deploy application
./scripts/deploy-zip.sh
```

### View Deployment Outputs
```bash
./scripts/get-aws-outputs.sh
```

---

## Notes

- **Deployment Time**: Typically 2-5 minutes
- **Zero Downtime**: Lambda deployments are zero-downtime (new version deployed, then traffic switched)
- **Rollback**: Use CloudFormation console to rollback if needed
- **Cost**: Lambda pay-per-request, no cost when idle

