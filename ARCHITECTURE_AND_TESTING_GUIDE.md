# Zapier Triggers API - Architecture and Testing Guide

## Table of Contents
1. [Overview](#overview)
2. [How the Application Works](#how-the-application-works)
3. [System Architecture](#system-architecture)
4. [Component Details](#component-details)
5. [Data Flow](#data-flow)
6. [Infrastructure](#infrastructure)
7. [Testing Guide](#testing-guide)

---

## Overview

The Zapier Triggers API is a serverless, event-driven system that provides a unified REST API for triggering Zapier workflows in real-time. It's built on AWS-native services with an asynchronous processing architecture that ensures high availability, scalability, and reliability.

### Key Features
- **Unified Event Ingestion**: Single REST endpoint for event submission
- **Real-Time Processing**: Sub-100ms latency for event acknowledgment
- **Dynamic Routing**: Automatic event routing based on payload content and subscriptions
- **Durable Storage**: All events persisted for audit and replay
- **Reliable Delivery**: At-least-once delivery with automatic retry logic
- **Rate Limiting**: Per-customer rate limiting with configurable quotas
- **Idempotency**: Support for idempotency keys to prevent duplicate events

---

## How the Application Works

### End-to-End Event Flow

```
1. Client → API Gateway → Lambda API
   ↓
2. Authentication & Rate Limiting
   ↓
3. Event Storage (DynamoDB)
   ↓
4. Queue Event (SQS)
   ↓
5. Return 202 Accepted (immediate response)
   ↓
6. Worker Lambda (triggered by SQS)
   ↓
7. Fetch Subscriptions (RDS PostgreSQL)
   ↓
8. Match Event to Subscriptions
   ↓
9. Deliver Webhooks (HTTP POST to Zapier)
   ↓
10. Update Event Status (DynamoDB)
```

### Step-by-Step Process

#### 1. Event Submission (`POST /api/v1/events`)

**Client Request:**
```json
POST /api/v1/events
Authorization: Bearer <api_key>
Content-Type: application/json

{
  "payload": {
    "event_type": "order.created",
    "order_id": "12345",
    "amount": 99.99,
    "customer_email": "user@example.com"
  }
}
```

**API Processing:**
1. **Authentication**: Extracts API key from `Authorization` header, validates against RDS PostgreSQL
2. **Rate Limiting**: Checks Redis for rate limit violations (per-customer quotas)
3. **Idempotency Check**: If idempotency key provided, checks Redis cache for duplicate requests
4. **Event Generation**: Creates unique event ID (UUID)
5. **Storage**: Stores event in DynamoDB with status "pending"
6. **Queueing**: Enqueues event to SQS queue
7. **Response**: Returns 202 Accepted immediately with event ID

**Response:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Event accepted for processing",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 2. Asynchronous Processing (Worker Lambda)

**SQS Trigger:**
- SQS EventSourceMapping automatically triggers Worker Lambda when messages arrive
- Lambda processes messages in batches (up to 10 messages, 5-second batching window)

**Worker Processing:**
1. **Message Parsing**: Extracts `customer_id`, `event_id`, `payload` from SQS message
2. **Subscription Lookup**: Queries RDS PostgreSQL for active subscriptions matching the customer
3. **Event Matching**: Uses `EventMatcher` to match event payload against subscription filters
4. **Webhook Delivery**: For each matching subscription:
   - Sends HTTP POST to subscription's webhook URL
   - Implements exponential backoff retry (up to 5 attempts)
   - Handles timeouts and errors gracefully
5. **Status Update**: Updates event status in DynamoDB:
   - `"unmatched"` - No subscriptions found or no matches
   - `"delivered"` - Successfully delivered to at least one subscription
   - `"failed"` - All delivery attempts failed

#### 3. Event Status Tracking

Events can be queried via the Inbox endpoint (`GET /api/v1/inbox`) which:
- Fetches events from DynamoDB for the authenticated customer
- Filters by status, date range, and other criteria
- Returns paginated results

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients                               │
│              (HTTP/REST API Consumers)                       │
└───────────────────────┬───────────────────────────────────────┘
                       │
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway                               │
│              (AWS API Gateway)                                │
└───────────────────────┬───────────────────────────────────────┘
                       │
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  API Lambda Function                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  FastAPI Application                                │   │
│  │  - Authentication (API Key)                         │   │
│  │  - Rate Limiting                                    │   │
│  │  - Idempotency                                      │   │
│  │  - Event Storage                                    │   │
│  │  - Queue Service                                    │   │
│  └─────────────────────────────────────────────────────┘   │
└───────────────────────┬───────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                              │
        ▼                              ▼
┌───────────────┐            ┌──────────────────┐
│  DynamoDB     │            │   SQS Queue      │
│  (Events)     │            │  (Event Queue)   │
└───────────────┘            └─────────┬─────────┘
                                       │
                                       │ SQS EventSourceMapping
                                       ▼
                          ┌────────────────────────────┐
                          │   Worker Lambda Function   │
                          │  ┌──────────────────────┐  │
                          │  │  Event Processor    │  │
                          │  │  - Message Parsing  │  │
                          │  │  - Subscription     │  │
                          │  │    Lookup           │  │
                          │  │  - Event Matching   │  │
                          │  │  - Webhook Delivery │  │
                          │  └──────────────────────┘  │
                          └───────────┬─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ RDS          │  │  DynamoDB    │  │  Zapier      │
            │ PostgreSQL   │  │  (Status     │  │  Webhooks    │
            │ (Subscriptions│  │   Updates)   │  │              │
            │  & API Keys) │  │              │  │              │
            └──────────────┘  └──────────────┘  └──────────────┘
                    │
                    │
                    ▼
            ┌──────────────┐
            │  ElastiCache │
            │  Redis       │
            │  (Caching)   │
            └──────────────┘
```

### Component Layers

#### 1. **API Layer** (FastAPI on Lambda)
- **Entry Point**: `app/main.py`
- **Routes**: `app/api/events.py`, `app/api/inbox.py`
- **Middleware**: Authentication, Rate Limiting, CORS
- **Handler**: `lambda_handler_zip.py` (Mangum adapter)

#### 2. **Core Services Layer**
- **Authentication** (`app/core/auth.py`): API key validation
- **Rate Limiting** (`app/core/rate_limiter.py`): Per-customer rate limits
- **Idempotency** (`app/core/idempotency.py`): Duplicate request prevention
- **Matching** (`app/core/matching.py`): Event-to-subscription matching logic

#### 3. **Business Logic Layer**
- **Event Storage** (`app/services/event_storage.py`): DynamoDB operations
- **Queue Service** (`app/services/queue_service.py`): SQS message enqueueing
- **Subscription Service** (`app/services/subscription_service.py`): RDS subscription queries
- **Webhook Service** (`app/services/webhook_service.py`): HTTP delivery with retries

#### 4. **Worker Layer**
- **Event Processor** (`app/workers/event_processor.py`): SQS message processing
- **Handler**: `lambda_worker_zip.py` (Lambda entry point)

#### 5. **Data Layer**
- **DynamoDB**: Event storage and status tracking
- **RDS PostgreSQL**: Subscriptions, API keys, customers
- **ElastiCache Redis**: Rate limiting, idempotency caching

---

## Component Details

### API Lambda Function

**Configuration:**
- Runtime: Python 3.11
- Memory: 1024 MB
- Timeout: 60 seconds
- VPC: Yes (for RDS access)
- Handler: `lambda_handler_zip.handler`

**Responsibilities:**
- Handle HTTP requests via API Gateway
- Authenticate requests using API keys
- Enforce rate limits
- Store events in DynamoDB
- Enqueue events to SQS
- Return immediate responses (202 Accepted)

**Key Files:**
- `lambda_handler_zip.py`: Lambda entry point (Mangum adapter)
- `app/main.py`: FastAPI application
- `app/api/events.py`: Event submission endpoint
- `app/api/inbox.py`: Event query endpoint

### Worker Lambda Function

**Configuration:**
- Runtime: Python 3.11
- Memory: 1024 MB
- Timeout: 300 seconds (5 minutes)
- VPC: Yes (for RDS access)
- Handler: `lambda_worker_zip.handler`
- Trigger: SQS EventSourceMapping (batch size: 10, batching window: 5s)

**Responsibilities:**
- Process SQS messages
- Fetch subscriptions from RDS
- Match events to subscriptions
- Deliver webhooks to Zapier
- Update event status in DynamoDB

**Key Files:**
- `lambda_worker_zip.py`: Lambda entry point
- `app/workers/event_processor.py`: Event processing logic

### Event Matching Logic

The `EventMatcher` class supports multiple matching strategies:

1. **Event Type Matching**: Simple string comparison
   ```json
   {
     "type": "event_type",
     "value": "order.created"
   }
   ```

2. **JSONPath Matching**: Field-based matching
   ```json
   {
     "type": "jsonpath",
     "expression": "$.event_type == 'order.created'"
   }
   ```

3. **Custom Matching**: Field operators (equals, not_equals, contains, exists)
   ```json
   {
     "type": "custom",
     "function": {
       "field": "amount",
       "operator": "greater_than",
       "value": 100
     }
   }
   ```

### Webhook Delivery

**Retry Strategy:**
- Maximum retries: 5 (configurable)
- Exponential backoff: Base 2, max delay 24 hours
- No retry on: 4xx errors (except 429), 410 Gone
- Retry on: 5xx errors, timeouts, network errors

**Response Handling:**
- 200/201: Success
- 410: Subscription invalid (mark for deactivation)
- 4xx: Client error (no retry)
- 5xx: Server error (retry with backoff)

---

## Data Flow

### Event Submission Flow

```
┌─────────┐
│ Client  │
└────┬────┘
     │ POST /api/v1/events
     │ Authorization: Bearer <api_key>
     │ { "payload": {...} }
     ▼
┌─────────────────────┐
│  API Gateway        │
└────┬────────────────┘
     │
     ▼
┌─────────────────────┐
│  API Lambda         │
│  ┌───────────────┐ │
│  │ 1. Auth       │ │ → RDS: Validate API key
│  │ 2. Rate Limit │ │ → Redis: Check rate limit
│  │ 3. Idempotency│ │ → Redis: Check idempotency key
│  │ 4. Generate ID│ │
│  │ 5. Store Event│ │ → DynamoDB: Store event (status: "pending")
│  │ 6. Enqueue    │ │ → SQS: Send message
│  └───────────────┘ │
└────┬────────────────┘
     │
     │ 202 Accepted
     │ { "event_id": "...", "status": "accepted" }
     ▼
┌─────────┐
│ Client  │ (receives immediate response)
└─────────┘
```

### Event Processing Flow

```
┌──────────────┐
│  SQS Queue   │
└──────┬───────┘
       │ Message arrives
       ▼
┌─────────────────────┐
│ EventSourceMapping │ (triggers Lambda)
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Worker Lambda      │
│  ┌───────────────┐ │
│  │ 1. Parse      │ │ Extract customer_id, event_id, payload
│  │    Message    │ │
│  │ 2. Fetch      │ │ → RDS: Get subscriptions for customer
│  │    Subscriptions│ │
│  │ 3. Match      │ │ Match event against subscription filters
│  │    Event      │ │
│  │ 4. Deliver    │ │ → HTTP POST: Send webhook to Zapier
│  │    Webhook    │ │   (with retry logic)
│  │ 5. Update     │ │ → DynamoDB: Update status
│  │    Status     │ │   ("delivered", "unmatched", or "failed")
│  └───────────────┘ │
└─────────────────────┘
```

### Status State Machine

```
┌─────────┐
│ pending │ (initial state after submission)
└────┬────┘
     │
     ├─────────────────┬──────────────────┐
     │                 │                  │
     ▼                 ▼                  ▼
┌──────────┐    ┌──────────┐    ┌──────────┐
│unmatched │    │delivered │    │  failed  │
└──────────┘    └──────────┘    └──────────┘
     │                 │                  │
     │                 │                  │
     └─────────────────┴──────────────────┘
                      │
                      ▼
              (final states)
```

---

## Infrastructure

### AWS Services

#### 1. **Lambda Functions**
- **API Function**: Handles HTTP requests
- **Worker Function**: Processes SQS messages
- **Deployment**: Zip deployment with Lambda Layers for dependencies
- **VPC Configuration**: Both functions in VPC for RDS access

#### 2. **API Gateway**
- **Type**: REST API
- **Integration**: Lambda Proxy Integration
- **Routes**: `/{proxy+}` and `/` (catch-all)

#### 3. **SQS**
- **Queue**: Standard queue for event processing
- **DLQ**: Dead Letter Queue for failed messages
- **EventSourceMapping**: Automatic Lambda triggering

#### 4. **DynamoDB**
- **Table**: Events storage
- **Partition Key**: `customer_id`
- **Sort Key**: `event_id`
- **Attributes**: `status`, `payload`, `timestamp`, `delivery_attempts`, etc.

#### 5. **RDS PostgreSQL**
- **Instance**: Managed PostgreSQL database
- **Tables**: 
  - `customers`: Customer information
  - `api_keys`: API key authentication
  - `subscriptions`: Zapier workflow subscriptions
- **Access**: Private subnet, accessible only from VPC

#### 6. **ElastiCache Redis**
- **Purpose**: Rate limiting and idempotency caching
- **Access**: Private subnet, accessible only from VPC

#### 7. **VPC Configuration**
- **Subnets**: Private subnets for Lambda and RDS
- **Security Groups**: Restrictive access rules
- **VPC Endpoints**: STS endpoint for IAM role credentials

### Infrastructure as Code

**Terraform** (`terraform/`):
- `main.tf`: Provider configuration
- `vpc.tf`: VPC, subnets, security groups
- `rds.tf`: PostgreSQL database
- `dynamodb.tf`: DynamoDB table
- `sqs.tf`: SQS queues
- `elasticache.tf`: Redis cluster
- `iam.tf`: IAM roles and policies
- `vpc_endpoints.tf`: VPC endpoints for AWS services

**SAM Template** (`template.zip.yaml`):
- Lambda function definitions
- API Gateway configuration
- Lambda Layers
- Environment variables
- Event source mappings

### Deployment

**Deployment Process:**
1. **Infrastructure**: Deploy via Terraform
   ```bash
   cd terraform
   terraform init
   terraform plan
   terraform apply
   ```

2. **Application**: Deploy via SAM
   ```bash
   # Build dependencies layer
   ./scripts/build-dependencies-layer.sh
   
   # Build function zip
   ./scripts/build-function-zip.sh
   
   # Deploy
   sam deploy --template-file template.zip.yaml --stack-name zapier-triggers-api-dev
   ```

---

## Testing Guide

### Testing Methods

The application uses **AWS RDS only** (no local database), so testing approaches differ based on your access level.

### Method 1: Test via Deployed Lambda API (Recommended)

This is the most reliable method since the Lambda functions have VPC access to RDS.

#### Prerequisites
- AWS CLI configured
- API endpoint URL (from Terraform outputs or AWS Console)
- Valid API key (from RDS database)

#### Step 1: Get API Endpoint

```bash
# From Terraform
cd terraform
terraform output api_gateway_url

# Or from AWS Console:
# API Gateway → Your API → Stages → Prod → Invoke URL
```

#### Step 2: Get API Key

API keys are stored in RDS. You can:
- Query RDS directly (if you have access)
- Check Lambda logs for customer creation
- Use known test keys (if available)

#### Step 3: Test Health Endpoint

```bash
export API_URL="https://your-api-id.execute-api.us-east-1.amazonaws.com/Prod"

curl "${API_URL}/health"
# Expected: {"status": "healthy", "environment": "dev"}
```

#### Step 4: Test Event Submission

```bash
export API_KEY="your-api-key-here"

curl -X POST "${API_URL}/api/v1/events" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "event_type": "order.created",
      "order_id": "test-123",
      "amount": 99.99,
      "customer_email": "test@example.com"
    }
  }' | python3 -m json.tool

# Expected response:
# {
#   "event_id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "accepted",
#   "message": "Event accepted for processing",
#   "timestamp": "2024-01-15T10:30:00Z"
# }
```

#### Step 5: Test Inbox Endpoint

```bash
curl "${API_URL}/api/v1/inbox" \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool

# Expected: List of events with their statuses
```

#### Step 6: Test with Idempotency Key

```bash
IDEMPOTENCY_KEY="test-key-$(date +%s)"

# First request
curl -X POST "${API_URL}/api/v1/events" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"event_type": "test"}}'

# Second request (should return same event_id)
curl -X POST "${API_URL}/api/v1/events" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Idempotency-Key: ${IDEMPOTENCY_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"payload": {"event_type": "test"}}'
```

#### Step 7: Monitor Worker Processing

```bash
# View API Lambda logs
aws logs tail /aws/lambda/zapier-triggers-api-dev-api --follow

# View Worker Lambda logs
aws logs tail /aws/lambda/zapier-triggers-api-dev-worker --follow

# Check SQS queue
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw sqs_queue_url) \
  --attribute-names ApproximateNumberOfMessages
```

### Method 2: Unit Testing

Run unit tests locally (these don't require AWS services):

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/test_events.py -v

# Run specific test
pytest tests/test_events.py::test_submit_event -v
```

**Test Files:**
- `tests/test_events.py`: Event submission tests
- `tests/test_auth.py`: Authentication tests
- `tests/test_idempotency.py`: Idempotency tests
- `tests/test_rate_limiter.py`: Rate limiting tests
- `tests/test_queue_service.py`: Queue service tests
- `tests/integration/`: Integration tests (require AWS)

### Method 3: Integration Testing

Integration tests require AWS services. They can be run:
- In AWS CloudShell
- From a machine with AWS credentials and VPC access
- Via CI/CD pipeline

```bash
# Run integration tests
pytest tests/integration/ -v

# With AWS credentials configured
AWS_PROFILE=your-profile pytest tests/integration/ -v
```

### Method 4: Manual Lambda Invocation

Test the worker Lambda directly:

```bash
# Create test event payload
cat > test-event.json <<EOF
{
  "Records": [
    {
      "messageId": "test-123",
      "body": "{\"customer_id\":\"test-customer\",\"event_id\":\"test-event\",\"payload\":{\"event_type\":\"test\"}}"
    }
  ]
}
EOF

# Invoke worker Lambda
aws lambda invoke \
  --function-name zapier-triggers-api-dev-worker \
  --payload file://test-event.json \
  response.json

# Check response
cat response.json | python3 -m json.tool
```

### Method 5: Frontend Testing (If Available)

If the frontend is deployed:

```bash
cd frontend
npm run dev

# Open http://localhost:5173
# Enter API URL and API key
# Submit events via UI
```

### Testing Checklist

#### API Endpoints
- [ ] Health endpoint returns 200
- [ ] Root endpoint returns API info
- [ ] Events endpoint accepts valid requests
- [ ] Events endpoint rejects invalid API keys (401)
- [ ] Events endpoint enforces rate limits (429)
- [ ] Events endpoint handles idempotency keys
- [ ] Inbox endpoint returns events for authenticated customer
- [ ] Inbox endpoint filters by status

#### Worker Processing
- [ ] Worker Lambda processes SQS messages
- [ ] Worker fetches subscriptions from RDS
- [ ] Worker matches events to subscriptions
- [ ] Worker delivers webhooks successfully
- [ ] Worker updates event status correctly
- [ ] Worker handles missing subscriptions (unmatched)
- [ ] Worker handles webhook failures (failed status)
- [ ] Worker retries failed webhooks

#### Data Flow
- [ ] Events stored in DynamoDB
- [ ] Events enqueued to SQS
- [ ] Events processed by worker
- [ ] Event status updated in DynamoDB
- [ ] Subscriptions queried from RDS
- [ ] Rate limits cached in Redis
- [ ] Idempotency keys cached in Redis

#### Error Handling
- [ ] Invalid API key returns 401
- [ ] Rate limit exceeded returns 429
- [ ] Invalid payload returns 400
- [ ] SQS failures are logged
- [ ] RDS connection failures are handled
- [ ] Webhook timeouts are retried
- [ ] Failed messages go to DLQ

### Monitoring and Debugging

#### CloudWatch Logs

```bash
# API Lambda logs
aws logs tail /aws/lambda/zapier-triggers-api-dev-api --follow

# Worker Lambda logs
aws logs tail /aws/lambda/zapier-triggers-api-dev-worker --follow

# Filter for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/zapier-triggers-api-dev-api \
  --filter-pattern "ERROR"
```

#### CloudWatch Metrics

```bash
# API Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=zapier-triggers-api \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Lambda invocation metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=zapier-triggers-api-dev-api \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

#### DynamoDB Inspection

```bash
# Scan events table
aws dynamodb scan \
  --table-name zapier-triggers-api-dev-events \
  --limit 10

# Query specific customer
aws dynamodb query \
  --table-name zapier-triggers-api-dev-events \
  --key-condition-expression "customer_id = :cid" \
  --expression-attribute-values '{":cid":{"S":"customer-123"}}'
```

#### SQS Queue Inspection

```bash
# Get queue attributes
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw sqs_queue_url) \
  --attribute-names All

# Receive messages (for debugging - don't do this in production!)
aws sqs receive-message \
  --queue-url $(terraform output -raw sqs_queue_url) \
  --max-number-of-messages 1
```

### Common Testing Scenarios

#### Scenario 1: Happy Path
1. Submit event with valid API key
2. Verify 202 Accepted response
3. Wait 5-10 seconds
4. Check inbox - event should be "delivered" or "unmatched"
5. Verify webhook was called (if subscription exists)

#### Scenario 2: No Subscriptions
1. Submit event for customer with no subscriptions
2. Verify 202 Accepted response
3. Wait 5-10 seconds
4. Check inbox - event should be "unmatched"

#### Scenario 3: Rate Limiting
1. Submit many events rapidly (exceed rate limit)
2. Verify 429 Too Many Requests after limit
3. Wait for rate limit window to reset
4. Submit again - should succeed

#### Scenario 4: Idempotency
1. Submit event with idempotency key
2. Submit same event again with same key
3. Verify both return same event_id
4. Verify only one event in DynamoDB

#### Scenario 5: Webhook Failure
1. Create subscription with invalid webhook URL
2. Submit matching event
3. Wait for processing
4. Check inbox - event should be "failed"
5. Verify retry attempts in logs

### Troubleshooting

#### "Invalid API key" Error
- **Check**: API key exists in RDS
- **Check**: Lambda can connect to RDS (check CloudWatch logs)
- **Check**: API key is active status in database

#### "Connection timeout" from Local Machine
- **Expected**: RDS is in private subnet
- **Solution**: Test via Lambda API, not directly

#### Events Stuck on "pending"
- **Check**: SQS queue has messages
- **Check**: Worker Lambda is enabled
- **Check**: EventSourceMapping is active
- **Check**: Worker Lambda logs for errors

#### "RDS configuration is required" Error
- **Check**: `.env` file has `RDS_ENDPOINT`, `RDS_USERNAME`, `RDS_PASSWORD`
- **Check**: Environment variables are loaded in Lambda

#### Worker Lambda Not Processing
- **Check**: EventSourceMapping is enabled
- **Check**: Worker Lambda has VPC permissions
- **Check**: Security groups allow RDS access
- **Check**: Worker Lambda logs for errors

---

## Summary

The Zapier Triggers API is a serverless, event-driven system that:

1. **Accepts events** via REST API with authentication and rate limiting
2. **Stores events** in DynamoDB and queues them in SQS
3. **Processes events** asynchronously via Worker Lambda
4. **Matches events** to subscriptions using flexible matching logic
5. **Delivers webhooks** to Zapier workflows with retry logic
6. **Tracks status** of all events for audit and debugging

The architecture is designed for:
- **High Availability**: Serverless, auto-scaling components
- **Reliability**: Durable storage, retry logic, DLQ
- **Performance**: Sub-100ms API response times
- **Scalability**: Handles high event volumes
- **Observability**: Comprehensive logging and metrics

For testing, use the deployed Lambda API (Method 1) as it has proper VPC access to all AWS services. Local testing is limited due to RDS being in a private subnet, but unit tests can be run locally without AWS services.

