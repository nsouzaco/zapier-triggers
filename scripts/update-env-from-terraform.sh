#!/bin/bash
# Update .env file with Terraform outputs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/terraform"
ENV_FILE="$PROJECT_ROOT/.env"

cd "$TERRAFORM_DIR"

if [ ! -d ".terraform" ]; then
    echo "❌ Terraform not initialized. Run: ./scripts/setup-aws.sh"
    exit 1
fi

echo "📝 Updating .env file with Terraform outputs..."
echo ""

# Get outputs
SQS_QUEUE_URL=$(terraform output -raw sqs_event_queue_url 2>/dev/null || echo "")
SQS_DLQ_URL=$(terraform output -raw sqs_dlq_url 2>/dev/null || echo "")
DYNAMODB_TABLE=$(terraform output -raw dynamodb_table_name 2>/dev/null || echo "")
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint 2>/dev/null || echo "")
REDIS_PORT=$(terraform output -raw redis_port 2>/dev/null || echo "6379")
RDS_ENDPOINT=$(terraform output -raw rds_endpoint 2>/dev/null || echo "")
RDS_DB_URL=$(terraform output -raw rds_database_url 2>/dev/null || echo "")

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  .env file not found. Creating from example..."
    if [ -f "$PROJECT_ROOT/.env.example" ]; then
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE"
    else
        echo "❌ .env.example not found"
        exit 1
    fi
fi

# Update .env file
if [ -n "$SQS_QUEUE_URL" ]; then
    sed -i.bak "s|SQS_EVENT_QUEUE_URL=.*|SQS_EVENT_QUEUE_URL=$SQS_QUEUE_URL|" "$ENV_FILE"
    echo "✅ Updated SQS_EVENT_QUEUE_URL"
fi

if [ -n "$SQS_DLQ_URL" ]; then
    sed -i.bak "s|SQS_DLQ_URL=.*|SQS_DLQ_URL=$SQS_DLQ_URL|" "$ENV_FILE"
    echo "✅ Updated SQS_DLQ_URL"
fi

if [ -n "$DYNAMODB_TABLE" ]; then
    sed -i.bak "s|DYNAMODB_EVENTS_TABLE=.*|DYNAMODB_EVENTS_TABLE=$DYNAMODB_TABLE|" "$ENV_FILE"
    echo "✅ Updated DYNAMODB_EVENTS_TABLE"
fi

if [ -n "$REDIS_ENDPOINT" ]; then
    # Extract host from endpoint (remove port if present)
    REDIS_HOST=$(echo "$REDIS_ENDPOINT" | cut -d: -f1)
    sed -i.bak "s|REDIS_HOST=.*|REDIS_HOST=$REDIS_HOST|" "$ENV_FILE"
    sed -i.bak "s|REDIS_PORT=.*|REDIS_PORT=$REDIS_PORT|" "$ENV_FILE"
    echo "✅ Updated REDIS_HOST and REDIS_PORT"
fi

if [ -n "$RDS_DB_URL" ]; then
    sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=$RDS_DB_URL|" "$ENV_FILE"
    echo "✅ Updated DATABASE_URL"
fi

# Clean up backup file
rm -f "$ENV_FILE.bak"

echo ""
echo "✅ .env file updated successfully!"
echo ""
echo "⚠️  Note: RDS password is sensitive. Make sure to update it securely."
echo "   You may want to use AWS Secrets Manager for production."

