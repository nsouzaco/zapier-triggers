# AWS Deployment Guide

This guide walks you through deploying the Zapier Triggers API to AWS.

## Prerequisites

1. **AWS Account**: You need an AWS account with appropriate permissions
2. **AWS CLI**: Install and configure AWS CLI
   ```bash
   aws configure
   ```
3. **Terraform**: Install Terraform >= 1.0
   ```bash
   # macOS
   brew install terraform
   
   # Or download from https://www.terraform.io/downloads
   ```
4. **jq**: Install jq for JSON parsing (optional but helpful)
   ```bash
   brew install jq
   ```

## Quick Start

### 1. Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your configuration:
- Set `rds_password` to a secure password
- Update `subnet_ids` with your VPC subnet IDs
- Update `allowed_cidr_blocks` with your VPC CIDR blocks
- Adjust instance sizes as needed

### 2. Deploy Infrastructure

```bash
# Option 1: Use the setup script
./scripts/setup-aws.sh

# Option 2: Use Makefile
make aws-setup

# Option 3: Manual Terraform commands
cd terraform
terraform init
terraform plan
terraform apply
```

### 3. Update Environment Variables

After deployment, update your `.env` file with the outputs:

```bash
# Option 1: Use the update script
./scripts/update-env-from-terraform.sh

# Option 2: Use Makefile
make update-env

# Option 3: Manual
make aws-outputs
# Then manually update .env file
```

### 4. Run Database Migrations

```bash
make migrate
```

### 5. Start the Application

```bash
make run
```

## Infrastructure Components

### SQS Queue
- **Event Queue**: Main queue for event ingestion
- **DLQ**: Dead-letter queue for failed events
- **Features**:
  - Long polling (20 seconds)
  - Message retention: 14 days
  - Visibility timeout: 5 minutes

### DynamoDB Table
- **Table Name**: `triggers-api-events-{environment}`
- **Partition Key**: `customer_id`
- **Sort Key**: `event_id`
- **Features**:
  - On-demand billing
  - TTL enabled (90 days default)
  - Point-in-time recovery
  - Encryption at rest

### RDS PostgreSQL
- **Instance**: Managed PostgreSQL 15.4
- **Features**:
  - Automatic backups (7 days)
  - Encryption at rest
  - Multi-AZ available for production

### ElastiCache Redis
- **Cluster**: Redis for rate limiting and idempotency
- **Features**:
  - Single node for dev
  - Multi-AZ for production
  - Encryption at rest

### IAM Roles
- **API Role**: Permissions for SQS, DynamoDB, ElastiCache
- **Worker Role**: Permissions for SQS, DynamoDB, RDS, ElastiCache

## Configuration

### Environment Variables

After deployment, your `.env` file should include:

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key

# SQS
SQS_EVENT_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/queue-name
SQS_DLQ_URL=https://sqs.us-east-1.amazonaws.com/123456789/dlq-name

# DynamoDB
DYNAMODB_EVENTS_TABLE=triggers-api-events-dev

# Redis
REDIS_HOST=your-redis-endpoint.cache.amazonaws.com
REDIS_PORT=6379

# RDS
DATABASE_URL=postgresql://user:password@rds-endpoint:5432/triggers_api
```

### Network Configuration

For production, ensure:
- RDS and ElastiCache are in private subnets
- Security groups restrict access appropriately
- Use VPC endpoints for AWS services
- Enable transit encryption for Redis

## Running the Worker

The SQS worker processes events from the queue:

```bash
# Option 1: Direct
python scripts/worker.py

# Option 2: Makefile
make worker
```

For production, deploy the worker as:
- **AWS Lambda**: With SQS trigger
- **ECS Task**: Long-running task
- **EC2 Instance**: With auto-scaling

## Monitoring

### CloudWatch Metrics

Monitor:
- SQS queue depth
- DynamoDB read/write capacity
- RDS connection count
- ElastiCache memory usage

### Logs

Logs are available in CloudWatch Logs:
- API logs: `/aws/lambda/zapier-triggers-api`
- Worker logs: `/aws/lambda/zapier-triggers-worker`

## Cost Optimization

### Development
- Use `db.t3.micro` for RDS
- Use `cache.t3.micro` for Redis
- Use on-demand DynamoDB billing

### Production
- Use reserved instances for RDS
- Use provisioned capacity for DynamoDB (if predictable traffic)
- Enable auto-scaling for all services

## Security Best Practices

1. **Secrets Management**: Use AWS Secrets Manager for passwords
2. **IAM Roles**: Use IAM roles instead of access keys when possible
3. **VPC**: Deploy resources in private subnets
4. **Encryption**: Enable encryption at rest and in transit
5. **Security Groups**: Restrict access to minimum required
6. **Network**: Use VPC endpoints for AWS services

## Troubleshooting

### Terraform Errors

**Error: "No valid credential sources found"**
- Run `aws configure` to set up credentials

**Error: "Subnet not found"**
- Update `subnet_ids` in `terraform.tfvars` with valid subnet IDs

**Error: "Insufficient permissions"**
- Ensure IAM user/role has required permissions

### Application Errors

**Error: "Cannot connect to RDS"**
- Check security group rules
- Verify subnet configuration
- Check RDS endpoint in `.env`

**Error: "Cannot connect to Redis"**
- Check security group rules
- Verify Redis endpoint
- Check network connectivity

**Error: "SQS queue not found"**
- Verify queue URL in `.env`
- Check IAM permissions

## Cleanup

To destroy all infrastructure:

```bash
cd terraform
terraform destroy
```

⚠️ **Warning**: This will delete all resources including data!

## Next Steps

1. Set up CI/CD pipeline
2. Configure monitoring and alerts
3. Set up backup strategies
4. Implement disaster recovery
5. Configure auto-scaling

