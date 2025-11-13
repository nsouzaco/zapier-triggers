# Terraform Infrastructure for Zapier Triggers API

This directory contains Terraform configurations for provisioning AWS infrastructure.

## Prerequisites

- AWS CLI installed and configured
- Terraform >= 1.0 installed
- AWS account with appropriate permissions

## Quick Start

1. **Copy the example variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit `terraform.tfvars` with your configuration:**
   - Update subnet IDs for your VPC
   - Set RDS password
   - Configure allowed CIDR blocks
   - Adjust instance sizes as needed

3. **Run the setup script:**
   ```bash
   ./scripts/setup-aws.sh
   ```

   Or manually:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## Infrastructure Components

### SQS
- Event queue for ingesting events
- Dead-letter queue for failed events
- Long polling enabled (20 seconds)
- Message retention: 14 days

### DynamoDB
- Events table with customer_id (partition key) and event_id (sort key)
- On-demand billing mode
- TTL enabled for automatic cleanup
- Point-in-time recovery enabled
- Encryption at rest enabled

### RDS PostgreSQL
- Managed PostgreSQL database for subscriptions
- Automatic backups (7 days retention)
- Encryption at rest
- Configurable instance class and storage

### ElastiCache Redis
- Redis cluster for rate limiting and idempotency
- Single node for dev, multi-AZ for production
- Encryption at rest enabled

### IAM
- API role with permissions for SQS, DynamoDB, ElastiCache
- Worker role with permissions for SQS, DynamoDB, RDS, ElastiCache
- Least privilege principle applied

## Outputs

After applying, get outputs with:
```bash
terraform output
```

Or use the helper script:
```bash
./scripts/get-aws-outputs.sh
```

## Environment Variables

After deployment, update your `.env` file with:

```bash
# Get outputs
terraform output -json > outputs.json

# Extract values (example)
SQS_EVENT_QUEUE_URL=$(jq -r '.sqs_event_queue_url.value' outputs.json)
DYNAMODB_EVENTS_TABLE=$(jq -r '.dynamodb_table_name.value' outputs.json)
REDIS_HOST=$(jq -r '.redis_endpoint.value' outputs.json)
DATABASE_URL=$(jq -r '.rds_database_url.value' outputs.json)
```

## Destroying Infrastructure

⚠️ **Warning**: This will delete all resources!

```bash
terraform destroy
```

## Variables

See `variables.tf` for all available variables.

Key variables:
- `aws_region`: AWS region (default: us-east-1)
- `environment`: Environment name (dev, staging, prod)
- `rds_instance_class`: RDS instance size
- `redis_node_type`: Redis node size
- `subnet_ids`: VPC subnet IDs
- `allowed_cidr_blocks`: Allowed CIDR blocks for security groups

## State Management

For production, configure remote state in `main.tf`:

```hcl
backend "s3" {
  bucket = "your-terraform-state-bucket"
  key    = "zapier-triggers-api/terraform.tfstate"
  region = "us-east-1"
}
```

## Security Notes

- RDS password should be stored in AWS Secrets Manager in production
- Use VPC endpoints for private communication
- Enable transit encryption for Redis in production
- Review and adjust security group rules
- Enable deletion protection for production environments

