# Zapier Triggers API - Comprehensive Architecture Summary

## Executive Overview

The Zapier Triggers API is a serverless, event-driven system that provides a unified REST API for triggering Zapier workflows in real-time. The architecture is built on AWS-native services with a fully asynchronous processing model, designed for high availability, scalability, and reliability.

**Key Characteristics:**
- **Serverless Architecture**: AWS Lambda for compute, auto-scaling by design
- **Event-Driven Processing**: Asynchronous message queue pattern with SQS
- **Multi-Database Architecture**: DynamoDB for events, RDS PostgreSQL for metadata, Redis for caching
- **Separation of Concerns**: API layer, processing layer, and storage layer are fully decoupled
- **Production-Ready**: VPC networking, IAM roles, encryption, monitoring

---

## System Architecture Overview

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │
│  │   Frontend   │  │  Demo Backend │  │ External APIs │                │
│  │  (React/Vite)│  │  (FastAPI)    │  │  (Any System) │                │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │
└─────────┼─────────────────┼──────────────────┼─────────────────────────┘
          │                 │                  │
          │ HTTPS           │ HTTPS            │ HTTPS
          └─────────────────┴──────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                                │
│                    AWS API Gateway (REST API)                            │
│                    - Request routing                                     │
│                    - SSL/TLS termination                                 │
│                    - Request/response transformation                     │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API LAMBDA LAYER                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application (lambda_handler_zip.py)                    │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  Middleware Stack                                          │  │  │
│  │  │  - CORS                                                     │  │  │
│  │  │  - Rate Limiting (Redis)                                    │  │  │
│  │  │  - Authentication (API Key → RDS)                          │  │  │
│  │  │  - Idempotency (Redis)                                     │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  API Endpoints                                               │  │  │
│  │  │  - POST /api/v1/events (Event submission)                   │  │  │
│  │  │  - GET /api/v1/inbox (Event retrieval)                      │  │  │
│  │  │  - GET /health (Health check)                                │  │  │
│  │  │  - POST /admin/test-customer (Dev only)                      │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────┬───────────────────────────────┬─────────────────────────┘
                │                               │
                │ Store Event                   │ Query Events
                ▼                               ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│      DynamoDB (Events)       │  │   RDS PostgreSQL            │
│  - Partition Key: customer_id│  │   - customers                │
│  - Sort Key: event_id       │  │   - api_keys                 │
│  - Status tracking           │  │   - subscriptions            │
│  - Full payload storage      │  │   - Event selectors          │
└──────────────────────────────┘  └──────────────────────────────┘
                │                               │
                │                               │
                └───────────────┬───────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      QUEUE LAYER (SQS)                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  SQS Standard Queue                                             │  │
│  │  - Durable message storage                                      │  │
│  │  - At-least-once delivery                                       │  │
│  │  - 14-day message retention                                     │  │
│  │  - Dead-letter queue integration                                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                │ SQS EventSourceMapping
                                │ (Batch: 10, Window: 5s)
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      WORKER LAMBDA LAYER                                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Event Processor (lambda_worker_zip.py)                          │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  1. Parse SQS Message                                      │  │  │
│  │  │  2. Fetch Subscriptions (RDS)                              │  │  │
│  │  │  3. Match Event to Subscriptions                            │  │  │
│  │  │  4. Deliver Webhooks (HTTP POST)                            │  │  │
│  │  │  5. Update Event Status (DynamoDB)                          │  │  │
│  │  │  6. Handle Retries & Errors                                │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└───────────────┬───────────────────────────────┬─────────────────────────┘
                │                               │
                │ Webhook Delivery              │ Status Updates
                ▼                               ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│   Zapier Workflow Engine     │  │   DynamoDB (Events)          │
│   (External Webhook URLs)    │  │   - Status: delivered/failed │
│                               │  │   - Delivery attempts       │
│                               │  │   - Timestamps              │
└──────────────────────────────┘  └──────────────────────────────┘
                │
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      CACHING LAYER (Redis)                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  ElastiCache Redis                                                │  │
│  │  - Rate limiting counters (per customer)                         │  │
│  │  - Idempotency key cache (24h TTL)                              │  │
│  │  - Session data (if needed)                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Frontend Architecture

### Technology Stack

- **Framework**: React 19.2.0 with modern hooks
- **Build Tool**: Vite 7.2.2 (fast HMR, optimized builds)
- **Styling**: Tailwind CSS 3.4.1 (utility-first CSS)
- **HTTP Client**: Native Fetch API
- **Deployment**: Static hosting (Vercel, Netlify, or S3)

### Frontend Structure

```
frontend/
├── src/
│   ├── App.jsx          # Main application component
│   ├── App.css          # Custom styles
│   └── main.jsx         # Entry point
├── public/              # Static assets
├── index.html           # HTML template
├── package.json         # Dependencies
├── vite.config.js       # Vite configuration
├── tailwind.config.cjs  # Tailwind configuration
└── vercel.json          # Vercel deployment config
```

### Frontend Features

#### 1. **Event Composer Tab**
- Form-based event creation with fields:
  - Document Type (text input)
  - Priority (dropdown: low/normal/high)
  - Description (textarea)
  - Customer Email (email input)
- Real-time form validation
- Submit button with loading states
- Success/error message display

#### 2. **Jira Ticket Analysis Tab**
- Large textarea for pasting Jira ticket text
- "Analyze & Submit Ticket" button
- Agent logic integration (via demo backend)
- Automatic urgency detection and submission

#### 3. **Event Inbox Tab**
- List view of all events with:
  - Event ID (monospace font)
  - Timestamp (formatted)
  - Status badge (color-coded: delivered/pending/failed/unmatched)
  - Expandable payload viewer (JSON)
- Refresh button
- Loading states
- Empty state messaging

### Frontend-Backend Communication

The frontend communicates with a **Demo Backend** (separate FastAPI service) rather than directly with the production Triggers API:

```
Frontend → Demo Backend → Production Triggers API
         ↓
      Resend API (email)
```

**Why this architecture?**
- Demo backend provides agent logic (decides whether to trigger)
- Demo backend sends demo emails via Resend API
- Frontend doesn't need API keys (demo backend handles authentication)
- Cleaner separation of concerns

### Frontend API Integration

**Endpoints Used:**
- `GET /demo/inbox` - Fetch events from production API (proxied)
- `POST /demo/trigger` - Submit event with agent logic
- `GET /health` - Health check

**Environment Configuration:**
- `VITE_DEMO_API_URL` - Demo backend URL (defaults to Railway deployment)
- No direct API key needed (demo backend handles auth)

### Frontend State Management

- **React Hooks**: `useState` for local state
- **No Redux/Context**: Simple component-level state
- **State Variables**:
  - `events`: Array of event objects
  - `loading`: Boolean for async operations
  - `error`: Error message string
  - `success`: Success message string
  - `activeTab`: Current tab selection
  - Form fields: `documentType`, `priority`, `description`, `customerEmail`

### Frontend Styling

- **Design System**: Zapier-inspired color scheme
  - Orange primary color (`#FF4A00`)
  - Gray scale for text and backgrounds
  - Clean, minimal interface
- **Responsive Design**: Mobile-friendly with Tailwind breakpoints
- **Component Styling**: Utility classes with hover states and transitions

---

## Backend API Architecture

### Technology Stack

- **Framework**: FastAPI (Python 3.11+)
- **Deployment**: AWS Lambda (serverless) with Mangum adapter
- **Language**: Python 3.11
- **Dependencies**: 
  - FastAPI for web framework
  - Pydantic for data validation
  - boto3 for AWS SDK
  - SQLAlchemy for PostgreSQL ORM
  - redis-py for Redis client
  - httpx for HTTP client (webhooks)

### Backend Structure

```
app/
├── main.py                    # FastAPI application entry point
├── config.py                  # Configuration management
├── api/                       # API route handlers
│   ├── events.py              # POST /api/v1/events
│   └── inbox.py               # GET /api/v1/inbox
├── core/                      # Core business logic
│   ├── auth.py                # API key authentication
│   ├── rate_limiter.py        # Rate limiting middleware
│   ├── idempotency.py         # Idempotency handling
│   └── matching.py           # Event-to-subscription matching
├── services/                  # Business logic services
│   ├── event_storage.py       # DynamoDB operations
│   ├── queue_service.py       # SQS message enqueueing
│   ├── subscription_service.py # RDS subscription queries
│   ├── webhook_service.py     # HTTP webhook delivery
│   ├── customer_service.py    # Customer management
│   └── email_service.py       # Email notifications (Resend)
├── workers/                   # Background workers
│   └── event_processor.py     # SQS message processing
├── models/                    # Pydantic models
│   ├── events.py              # Event request/response models
│   └── responses.py           # API response models
├── database/                  # Database models
│   └── models.py              # SQLAlchemy models
└── utils/                     # Utility functions
    ├── logging.py             # Logging configuration
    └── aws.py                 # AWS client initialization
```

### API Endpoints

#### 1. **POST /api/v1/events** - Event Submission

**Purpose**: Accept events and return immediate acknowledgment

**Request:**
```json
{
  "payload": {
    "event_type": "order.created",
    "order_id": "12345",
    "amount": 99.99,
    "customer_email": "user@example.com"
  }
}
```

**Headers:**
- `Authorization: Bearer <api_key>` (required)
- `Idempotency-Key: <key>` (optional)

**Response (202 Accepted):**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "accepted",
  "message": "Event accepted for processing",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Processing Flow:**
1. Extract API key from Authorization header
2. Validate API key → get `customer_id` from RDS
3. Check rate limit in Redis (per customer)
4. Check idempotency key in Redis (if provided)
5. Generate unique event ID (UUID)
6. Store event in DynamoDB with status "pending"
7. Enqueue event to SQS queue
8. Return 202 Accepted immediately

**Error Responses:**
- `401 Unauthorized`: Invalid or missing API key
- `429 Too Many Requests`: Rate limit exceeded
- `400 Bad Request`: Invalid payload
- `500 Internal Server Error`: Processing failure

#### 2. **GET /api/v1/inbox** - Event Retrieval

**Purpose**: Retrieve events for authenticated customer

**Query Parameters:**
- `event_type` (optional): Filter by event type
- `status` (optional): Filter by status (pending/delivered/failed/unmatched)
- `start_time` (optional): Start timestamp (ISO 8601)
- `end_time` (optional): End timestamp (ISO 8601)
- `limit` (optional): Max results (1-1000, default: 100)
- `cursor` (optional): Pagination cursor

**Headers:**
- `Authorization: Bearer <api_key>` (required)

**Response (200 OK):**
```json
{
  "events": [
    {
      "event_id": "550e8400-e29b-41d4-a716-446655440000",
      "customer_id": "customer-123",
      "payload": {...},
      "status": "delivered",
      "timestamp": "2024-01-15T10:30:00Z",
      "delivery_attempts": 1,
      "last_delivery_timestamp": "2024-01-15T10:30:05Z"
    }
  ],
  "total": 1,
  "cursor": null,
  "has_more": false
}
```

**Processing Flow:**
1. Extract API key → get `customer_id`
2. Query DynamoDB for events (partition key: `customer_id`)
3. Apply filters (status, event_type, time range)
4. Return paginated results

#### 3. **GET /health** - Health Check

**Purpose**: Service health monitoring

**Response (200 OK):**
```json
{
  "status": "healthy",
  "environment": "dev"
}
```

#### 4. **POST /admin/test-customer** - Create Test Customer (Dev Only)

**Purpose**: Development endpoint for creating test customers with API keys

**Request:**
```json
{
  "name": "Test Customer",
  "email": "test@example.com"
}
```

**Response:**
```json
{
  "customer_id": "customer-123",
  "api_key": "sk_test_...",
  "name": "Test Customer",
  "email": "test@example.com",
  "status": "active"
}
```

### API Middleware Stack

#### 1. **CORS Middleware**
- Allows all origins in development
- Configurable for production
- Supports credentials

#### 2. **Rate Limiting Middleware**
- Per-customer rate limiting
- Redis-backed counters
- Configurable limits (default: 1000 events/second)
- Returns `429 Too Many Requests` when exceeded

#### 3. **Authentication Middleware**
- Extracts API key from `Authorization: Bearer <key>` header
- Validates against RDS PostgreSQL `api_keys` table
- Returns `customer_id` for downstream processing
- Returns `401 Unauthorized` on failure

#### 4. **Idempotency Middleware**
- Extracts `Idempotency-Key` header (optional)
- Checks Redis cache for duplicate requests
- Returns cached response if key exists
- Caches response for 24 hours

### API Lambda Configuration

**Deployment:**
- **Handler**: `lambda_handler_zip.handler` (Mangum adapter)
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 60 seconds
- **VPC**: Yes (for RDS and Redis access)
- **Package**: Zip deployment with Lambda Layer for dependencies

**Environment Variables:**
- `ENVIRONMENT`: dev/production
- `LOG_LEVEL`: INFO/DEBUG
- `RDS_ENDPOINT`: PostgreSQL endpoint
- `RDS_USERNAME`: Database username
- `RDS_PASSWORD`: Database password
- `DYNAMODB_TABLE_NAME`: Events table name
- `SQS_EVENT_QUEUE_URL`: SQS queue URL
- `REDIS_ENDPOINT`: Redis endpoint
- `AWS_REGION`: AWS region

**IAM Permissions:**
- DynamoDB: Read/Write to events table
- SQS: SendMessage to event queue
- RDS: Connect and query (via VPC)
- ElastiCache: Connect and query (via VPC)
- CloudWatch: Write logs

---

## Worker Architecture

### Worker Lambda Function

**Purpose**: Process events from SQS queue asynchronously

**Deployment:**
- **Handler**: `lambda_worker_zip.handler`
- **Runtime**: Python 3.11
- **Memory**: 1024 MB
- **Timeout**: 300 seconds (5 minutes)
- **VPC**: Yes (for RDS and DynamoDB access)
- **Trigger**: SQS EventSourceMapping
  - Batch size: 10 messages
  - Batching window: 5 seconds
  - Maximum concurrency: Configurable

### Worker Processing Flow

```
SQS Message Arrives
    ↓
Lambda Triggered (EventSourceMapping)
    ↓
Parse SQS Message
    - Extract customer_id, event_id, payload
    ↓
Fetch Subscriptions (RDS PostgreSQL)
    - Query subscriptions table for customer_id
    - Filter by active status
    ↓
Match Event to Subscriptions
    - Use EventMatcher class
    - Support multiple matching strategies:
      * Event type matching
      * JSONPath matching
      * Custom field matching
    ↓
For Each Matching Subscription:
    ↓
Deliver Webhook (HTTP POST)
    - Send event payload to subscription.webhook_url
    - Implement exponential backoff retry
    - Max retries: 5
    - Handle 410 Gone (subscription invalid)
    ↓
Update Event Status (DynamoDB)
    - "delivered": Successfully delivered
    - "failed": All delivery attempts failed
    - "unmatched": No subscriptions matched
    ↓
Delete Message from SQS (automatic on success)
```

### Event Matching Logic

The `EventMatcher` class supports multiple matching strategies:

#### 1. **Event Type Matching**
```json
{
  "type": "event_type",
  "value": "order.created"
}
```

#### 2. **JSONPath Matching**
```json
{
  "type": "jsonpath",
  "expression": "$.event_type == 'order.created'"
}
```

#### 3. **Custom Field Matching**
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

The system delivers webhooks to subscription URLs when events match subscription criteria. Webhooks are fully implemented and operational.

#### Webhook Configuration

**Subscription Model:**
- Each subscription contains a `webhook_url` field stored in RDS PostgreSQL
- Webhook URLs are unique per subscription (workflow)
- Subscriptions are created via API endpoint or direct database insert

**Creating Subscriptions with Webhooks:**

1. **Via Admin API Endpoint** (Development):
```bash
POST /admin/test-subscription
{
  "customer_id": "customer-uuid",
  "event_selector": {
    "type": "event_type",
    "value": "order.created"
  },
  "webhook_url": "https://webhook.site/unique-url"
}
```

2. **Via Scripts:**
```bash
# Using create-subscription-via-lambda.py
python scripts/create-subscription-via-lambda.py \
  --customer-id "customer-uuid" \
  --event-type "order.created" \
  --webhook-url "https://webhook.site/unique-url"
```

3. **Direct Database Insert:**
```sql
INSERT INTO subscriptions (workflow_id, customer_id, event_selector, webhook_url, status)
VALUES (
  gen_random_uuid(),
  'customer-uuid',
  '{"type": "event_type", "value": "order.created"}'::jsonb,
  'https://webhook.site/unique-url',
  'active'
);
```

#### Webhook Payload Format

**Single Event Delivery:**
```json
[
  {
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "customer_id": "customer-123",
    "payload": {
      "event_type": "order.created",
      "order_id": "12345",
      "amount": 99.99,
      "customer_email": "user@example.com"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
]
```

**Batch Event Delivery:**
```json
[
  {
    "event_id": "event-1",
    "customer_id": "customer-123",
    "payload": {...},
    "timestamp": "2024-01-15T10:30:00Z"
  },
  {
    "event_id": "event-2",
    "customer_id": "customer-123",
    "payload": {...},
    "timestamp": "2024-01-15T10:30:01Z"
  }
]
```

**HTTP Request Details:**
- **Method**: POST
- **Content-Type**: `application/json`
- **User-Agent**: `Zapier-Triggers-API/1.0`
- **Body**: JSON array of events (Zapier-compatible format)

#### Retry Strategy

- **Maximum retries**: 5 (configurable via `webhook_max_retries`)
- **Exponential backoff**: Base 2, max delay 24 hours
- **No retry on**: 
  - 4xx errors (except 429 rate limit)
  - 410 Gone (subscription invalid)
- **Retry on**: 
  - 5xx server errors
  - Timeouts (30 seconds default)
  - Network errors

**Backoff Calculation:**
```
delay = min(2^attempt, max_delay_seconds)
Example: attempt 1 = 2s, attempt 2 = 4s, attempt 3 = 8s, ... up to 24 hours
```

#### Response Handling

- **`200/201`**: Success → mark event as "delivered" in DynamoDB
- **`410 Gone`**: Subscription invalid → mark subscription for deactivation, no retry
- **`4xx` (except 410)**: Client error → no retry, mark event as "failed"
- **`429`**: Rate limit → retry with backoff
- **`5xx`**: Server error → retry with exponential backoff
- **Timeout**: Retry with exponential backoff (30s default timeout)

#### Webhook URL Examples

**Testing Webhooks:**
- **webhook.site**: https://webhook.site (get unique URL, view requests in real-time)
- **RequestBin**: https://requestbin.com (similar to webhook.site)
- **Zapier Webhooks**: `https://hooks.zapier.com/hooks/catch/{path}/{id}`
- **Custom Endpoint**: Any HTTP endpoint that accepts POST requests

**Production Webhooks:**
- Zapier workflow execution engine URLs
- Custom application endpoints
- Third-party webhook receivers

#### Webhook Delivery Flow

```
1. Event matches subscription criteria
   ↓
2. Worker Lambda prepares webhook payload
   - Single event or batch of events
   - Includes event_id, customer_id, payload, timestamp
   ↓
3. HTTP POST to subscription.webhook_url
   - Headers: Content-Type, User-Agent
   - Body: JSON array of events
   ↓
4. Wait for response (30s timeout)
   ↓
5. Handle response:
   - Success (200/201) → Update event status to "delivered"
   - Failure → Retry with exponential backoff
   - 410 Gone → Mark subscription for deactivation
   ↓
6. Update DynamoDB with final status
```

#### Webhook Service Implementation

**Service Class**: `app/services/webhook_service.py`

**Key Methods:**
- `deliver_webhook()`: Single webhook delivery attempt
- `deliver_with_retry()`: Webhook delivery with exponential backoff retry

**HTTP Client:**
- Uses `httpx.AsyncClient` for async HTTP requests
- Timeout: 30 seconds (configurable)
- Follows redirects: Yes
- Connection pooling: Automatic

#### Webhook Monitoring

**Success Indicators:**
- Event status changes to "delivered" in DynamoDB
- `delivery_attempts` field shows number of attempts
- `last_delivery_timestamp` updated on success
- Webhook receiver (webhook.site, etc.) shows received request

**Failure Indicators:**
- Event status remains "failed" after max retries
- CloudWatch logs show retry attempts
- Dead Letter Queue (DLQ) receives messages after max retries
- Webhook receiver shows no requests (or error responses)

**Logging:**
- Success: `"Webhook delivered successfully: {workflow_id} ({n} events)"`
- Retry: `"Retrying webhook delivery in {delay}s (attempt {n}/{max})"`
- Failure: `"Webhook delivery failed after {n} attempts: {error}"`
- 410 Gone: `"Webhook returned 410 Gone: {workflow_id}. Subscription should be deactivated."`

#### Testing Webhooks

**Step 1: Create a Test Webhook URL**
- Visit https://webhook.site to get a unique URL
- Copy the URL (e.g., `https://webhook.site/abc123-def456-ghi789`)

**Step 2: Create a Subscription**
```bash
# Via API endpoint
curl -X POST "${API_URL}/admin/test-subscription" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "your-customer-id",
    "event_selector": {
      "type": "event_type",
      "value": "order.created"
    },
    "webhook_url": "https://webhook.site/your-unique-url"
  }'
```

**Step 3: Submit a Matching Event**
```bash
curl -X POST "${API_URL}/api/v1/events" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "event_type": "order.created",
      "order_id": "12345",
      "amount": 99.99
    }
  }'
```

**Step 4: Verify Webhook Delivery**
- Check webhook.site page - you should see the POST request
- Request body will contain JSON array with event data
- Check event status via `/api/v1/inbox` - should be "delivered"
- Check CloudWatch logs for delivery confirmation

**Step 5: Monitor Worker Logs**
```bash
aws logs tail /aws/lambda/zapier-triggers-api-dev-worker --follow
```

You should see:
- `"Found 1 subscriptions for customer {customer_id}"`
- `"Webhook delivered successfully: {workflow_id} (1 events)"`

### Worker Error Handling

**Batch Item Failures:**
- Lambda returns `batchItemFailures` array for failed messages
- SQS automatically retries failed messages
- After max retries, message goes to Dead Letter Queue (DLQ)

**Error Scenarios:**
- RDS connection failure → mark event as "unmatched", log error
- Subscription fetch failure → mark event as "unmatched"
- Webhook delivery failure → retry, then mark as "failed"
- DynamoDB update failure → log error, message retried by SQS

---

## Data Storage Architecture

### DynamoDB - Event Storage

**Table Name**: `zapier-triggers-api-{environment}-events`

**Schema:**
```
Partition Key: customer_id (String)
Sort Key: event_id (String)
Attributes:
  - payload (JSON/Map) - Full event payload
  - timestamp (String) - ISO 8601 timestamp
  - status (String) - pending/delivered/failed/unmatched
  - delivery_attempts (Number) - Number of delivery attempts
  - last_delivery_timestamp (String) - ISO 8601 timestamp
  - retry_count (Number) - Retry count
  - metadata (JSON/Map) - Additional metadata
TTL: configurable (default: 90 days)
```

**Access Patterns:**
- Write: Store event on submission (API Lambda)
- Read: Query events by customer_id (Inbox endpoint)
- Update: Update status after processing (Worker Lambda)

**Indexes:**
- Primary key: `customer_id` + `event_id`
- Global Secondary Index (GSI): `status` + `timestamp` (for filtering)

### RDS PostgreSQL - Metadata Storage

**Database**: `triggers_api`

**Tables:**

#### 1. **customers**
```sql
CREATE TABLE customers (
    customer_id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- active/inactive
    rate_limit_per_second INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 2. **api_keys**
```sql
CREATE TABLE api_keys (
    api_key VARCHAR(255) PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(customer_id),
    status VARCHAR(50) NOT NULL,  -- active/inactive
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    INDEX idx_customer_id (customer_id)
);
```

#### 3. **subscriptions**
```sql
CREATE TABLE subscriptions (
    workflow_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL REFERENCES customers(customer_id),
    event_selector JSONB NOT NULL,  -- Matching criteria
    webhook_url TEXT NOT NULL,      -- Webhook endpoint URL for event delivery
    status VARCHAR(50) NOT NULL,     -- active/disabled
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_customer_id (customer_id),
    INDEX idx_status (status)
);
```

**Webhook URL Storage:**
- Stored as `TEXT` field in `subscriptions` table
- Required field (NOT NULL)
- Unique per subscription (workflow)
- Can be updated when subscription is modified
- Examples:
  - `https://webhook.site/unique-id` (testing)
  - `https://hooks.zapier.com/hooks/catch/path/id` (Zapier)
  - `https://api.example.com/webhooks/events` (custom)

**Connection:**
- Private subnet (VPC)
- SSL/TLS encryption
- Connection pooling (SQLAlchemy)
- Read replicas for high query volume (future)

### ElastiCache Redis - Caching

**Purpose**: Rate limiting and idempotency caching

**Key Patterns:**

#### Rate Limiting
```
Key: rate_limit:{api_key}:{window_timestamp}
Value: count (integer)
TTL: rate_limit_window_seconds
```

#### Idempotency
```
Key: idempotency:{idempotency_key}
Value: {
    "event_id": "...",
    "response": {...},
    "timestamp": "..."
}
TTL: 24 hours
```

**Connection:**
- Private subnet (VPC)
- Redis cluster mode (high availability)
- Automatic failover

---

## Infrastructure Architecture

### AWS Services

#### 1. **Lambda Functions**
- **API Lambda**: Handles HTTP requests via API Gateway
- **Worker Lambda**: Processes SQS messages
- **Deployment**: Zip files with Lambda Layers for dependencies
- **VPC Configuration**: Both functions in VPC for RDS/Redis access

#### 2. **API Gateway**
- **Type**: REST API
- **Integration**: Lambda Proxy Integration
- **Routes**: `/{proxy+}` and `/` (catch-all)
- **CORS**: Configured in FastAPI middleware
- **SSL/TLS**: Automatic HTTPS termination

#### 3. **SQS**
- **Queue Type**: Standard queue (at-least-once delivery)
- **Dead Letter Queue**: For failed messages after max retries
- **EventSourceMapping**: Automatic Lambda triggering
- **Message Retention**: 14 days
- **Visibility Timeout**: 300 seconds (matches Lambda timeout)

#### 4. **DynamoDB**
- **Table**: Events storage
- **Mode**: On-demand (auto-scaling)
- **Encryption**: KMS encryption at rest
- **Backup**: Point-in-time recovery enabled

#### 5. **RDS PostgreSQL**
- **Instance Type**: db.t3.micro (dev) / db.t3.medium (production)
- **Multi-AZ**: Enabled for high availability
- **Backup**: Automated backups with 7-day retention
- **Encryption**: KMS encryption at rest
- **Network**: Private subnet, no public access

#### 6. **ElastiCache Redis**
- **Engine**: Redis 7.x
- **Mode**: Cluster mode (high availability)
- **Node Type**: cache.t3.micro (dev) / cache.t3.medium (production)
- **Network**: Private subnet, no public access

#### 7. **VPC Configuration**
- **Subnets**: 
  - Private subnets for Lambda, RDS, Redis
  - Public subnets for NAT Gateway
- **Security Groups**: Restrictive access rules
- **VPC Endpoints**: STS endpoint for IAM role credentials
- **NAT Gateway**: For Lambda outbound internet access (webhooks)

### Infrastructure as Code

#### Terraform (`terraform/`)
- **main.tf**: Provider configuration (AWS)
- **vpc.tf**: VPC, subnets, security groups, route tables
- **rds.tf**: PostgreSQL database instance
- **dynamodb.tf**: DynamoDB table
- **sqs.tf**: SQS queues (main + DLQ)
- **elasticache.tf**: Redis cluster
- **iam.tf**: IAM roles and policies
- **vpc_endpoints.tf**: VPC endpoints for AWS services
- **nat_gateway.tf**: NAT Gateway for outbound internet
- **outputs.tf**: Infrastructure outputs (endpoints, ARNs)

#### SAM Template (`template.zip.yaml`)
- **API Lambda**: Function definition with environment variables
- **Worker Lambda**: Function definition with SQS trigger
- **Lambda Layers**: Dependencies layer
- **API Gateway**: REST API configuration
- **EventSourceMapping**: SQS → Worker Lambda trigger

### Deployment Process

#### 1. **Infrastructure Deployment (Terraform)**
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

#### 2. **Application Deployment (SAM)**
```bash
# Build dependencies layer
./scripts/build-lambda-layer.sh

# Build function zip
./scripts/build-function-zip.sh

# Deploy
sam deploy --template-file template.zip.yaml \
  --stack-name zapier-triggers-api-dev \
  --parameter-overrides \
    SqsEventQueueUrl=<queue-url> \
    RdsEndpoint=<rds-endpoint> \
    ...
```

### Networking Architecture

**VPC Design:**
```
┌─────────────────────────────────────────────────────────┐
│  VPC (10.0.0.0/16)                                      │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Public Subnet   │  │  Public Subnet   │            │
│  │  (10.0.1.0/24)   │  │  (10.0.2.0/24)   │            │
│  │                  │  │                  │            │
│  │  NAT Gateway     │  │  (Reserved)      │            │
│  └──────────────────┘  └──────────────────┘            │
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Private Subnet  │  │  Private Subnet  │            │
│  │  (10.0.3.0/24)   │  │  (10.0.4.0/24)   │            │
│  │                  │  │                  │            │
│  │  Lambda (API)    │  │  Lambda (Worker)│            │
│  │  RDS PostgreSQL  │  │  ElastiCache     │            │
│  │  DynamoDB (VPC)  │  │  Redis           │            │
│  └──────────────────┘  └──────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

**Security Groups:**
- **Lambda Security Group**: 
  - Outbound: All traffic (for webhooks, AWS services)
  - Inbound: None (Lambda invoked by AWS services)
- **RDS Security Group**:
  - Inbound: From Lambda security group (port 5432)
  - Outbound: None
- **Redis Security Group**:
  - Inbound: From Lambda security group (port 6379)
  - Outbound: None

---

## Demo Backend Architecture

### Purpose

The Demo Backend is a separate FastAPI application that orchestrates demo workflows. It acts as an intermediary between the frontend and the production Triggers API, providing:

1. **Agent Logic**: Decides whether to trigger events based on form data
2. **API Integration**: Calls production Triggers API with proper authentication
3. **Email Service**: Sends demo emails via Resend API
4. **Frontend Proxy**: Simplifies frontend by handling API keys and authentication

### Technology Stack

- **Framework**: FastAPI
- **Deployment**: Railway (or any PaaS)
- **Dependencies**: 
  - `requests` for HTTP calls
  - `python-dotenv` for environment variables

### Demo Backend Endpoints

#### 1. **POST /demo/trigger**
- Receives form data from frontend
- Runs agent logic (`should_trigger_event()`)
- If triggered: calls production Triggers API
- Sends demo email via Resend API
- Returns complete status

#### 2. **GET /demo/inbox**
- Proxies request to production Triggers API
- Returns events list to frontend

#### 3. **GET /health**
- Health check endpoint

### Agent Logic

The `should_trigger_event()` function implements simple rule-based logic:

```python
def should_trigger_event(document_type, priority, description):
    urgent_keywords = ["angry", "urgent", "critical", "escalate", "emergency"]
    
    if priority.lower() == "high":
        return True, "Priority is high"
    
    if any(keyword in description.lower() for keyword in urgent_keywords):
        return True, "Description contains urgent keywords"
    
    return False, "Priority is normal and no urgent keywords detected"
```

### Integration Flow

```
Frontend submits form
    ↓
Demo Backend receives request
    ↓
Agent logic decides: trigger or not?
    ↓
If triggered:
    ├─→ Call Production Triggers API (POST /api/v1/events)
    └─→ Send demo email via Resend API
    ↓
Return status to frontend
```

---

## Data Flow Patterns

### Event Submission Flow

```
1. Client → API Gateway
   POST /api/v1/events
   Authorization: Bearer <api_key>
   { "payload": {...} }
   
2. API Gateway → API Lambda
   (Lambda Proxy Integration)
   
3. API Lambda Processing:
   a. Extract API key from header
   b. Validate API key → get customer_id (RDS)
   c. Check rate limit (Redis)
   d. Check idempotency key (Redis, if provided)
   e. Generate event_id (UUID)
   f. Store event in DynamoDB (status: "pending")
   g. Enqueue to SQS
   
4. API Lambda → Client
   202 Accepted
   { "event_id": "...", "status": "accepted" }
   
5. SQS → Worker Lambda (asynchronous)
   (EventSourceMapping triggers Lambda)
   
6. Worker Lambda Processing:
   a. Parse SQS message
   b. Fetch subscriptions (RDS)
   c. Match event to subscriptions
   d. Deliver webhooks (HTTP POST)
   e. Update event status (DynamoDB)
   
7. Worker Lambda → SQS
   Delete message (on success)
```

### Event Retrieval Flow

```
1. Client → API Gateway
   GET /api/v1/inbox?status=delivered&limit=100
   Authorization: Bearer <api_key>
   
2. API Gateway → API Lambda
   
3. API Lambda Processing:
   a. Extract API key → get customer_id (RDS)
   b. Query DynamoDB (partition key: customer_id)
   c. Apply filters (status, event_type, time range)
   d. Return paginated results
   
4. API Lambda → Client
   200 OK
   { "events": [...], "total": 10, "has_more": false }
```

### Webhook Delivery Flow

```
1. Worker Lambda processes event
   ↓
2. Event matched to subscription(s)
   ↓
3. For each matching subscription:
   a. Prepare webhook payload (JSON array format)
      [
        {
          "event_id": "550e8400-e29b-41d4-a716-446655440000",
          "customer_id": "customer-123",
          "payload": {
            "event_type": "order.created",
            "order_id": "12345",
            "amount": 99.99
          },
          "timestamp": "2024-01-15T10:30:00Z"
        }
      ]
   
   b. HTTP POST to subscription.webhook_url
      - Method: POST
      - Headers: Content-Type: application/json, User-Agent: Zapier-Triggers-API/1.0
      - Body: JSON array of events
      - Timeout: 30 seconds (configurable)
      - Follow redirects: Yes
   
   c. Wait for response
   
   d. Handle response:
      - 200/201: Success → mark event as "delivered" in DynamoDB
      - 410 Gone: Subscription invalid → mark subscription for deactivation, no retry
      - 4xx (except 410): Client error → no retry, mark event as "failed"
      - 429: Rate limit → retry with exponential backoff
      - 5xx: Server error → retry with exponential backoff (up to 5 attempts)
      - Timeout: Retry with exponential backoff
   
   e. Retry Logic (if needed):
      - Attempt 1: Immediate
      - Attempt 2: 2 seconds delay
      - Attempt 3: 4 seconds delay
      - Attempt 4: 8 seconds delay
      - Attempt 5: 16 seconds delay
      - Max delay: 24 hours
   
4. Update event status in DynamoDB
   - "delivered": At least one webhook succeeded
   - "failed": All webhook delivery attempts failed
   - "unmatched": No subscriptions matched the event
   
5. Log results to CloudWatch
   - Success: Info log with workflow_id and event count
   - Failure: Error log with attempt count and error message
   - 410 Gone: Warning log with deactivation recommendation
```

---

## Security Architecture

### Authentication

- **Method**: API Key (Bearer token)
- **Storage**: RDS PostgreSQL `api_keys` table
- **Validation**: Per-request lookup in RDS
- **Header Format**: `Authorization: Bearer <api_key>`

### Authorization

- **Customer Isolation**: All queries filtered by `customer_id`
- **Data Segregation**: Events stored with `customer_id` partition key
- **No Cross-Customer Access**: API key → customer_id mapping ensures isolation

### Encryption

- **In Transit**: HTTPS/TLS 1.2+ (API Gateway)
- **At Rest**: 
  - DynamoDB: KMS encryption
  - RDS: KMS encryption
  - ElastiCache: Encryption in transit (optional)

### Network Security

- **VPC**: All resources in private subnets
- **Security Groups**: Restrictive access rules
- **No Public Access**: RDS and Redis not publicly accessible
- **NAT Gateway**: Lambda outbound internet for webhooks only

### Rate Limiting

- **Per-Customer Limits**: Configurable (default: 1000 events/second)
- **Storage**: Redis counters
- **Window**: Sliding window (1 second)
- **Response**: `429 Too Many Requests` when exceeded

### Idempotency

- **Key**: `Idempotency-Key` header (optional)
- **Storage**: Redis cache (24-hour TTL)
- **Behavior**: Return cached response for duplicate keys
- **Prevents**: Duplicate event processing

---

## Monitoring and Observability

### Logging

- **Format**: Structured JSON logging
- **Destination**: CloudWatch Logs
- **Log Groups**:
  - `/aws/lambda/zapier-triggers-api-dev-api`
  - `/aws/lambda/zapier-triggers-api-dev-worker`
- **Log Levels**: INFO, DEBUG, WARNING, ERROR

### Metrics (CloudWatch)

**API Lambda Metrics:**
- Invocations
- Duration (P50, P95, P99)
- Errors
- Throttles

**Worker Lambda Metrics:**
- Invocations
- Duration
- Errors
- Dead-letter queue messages

**SQS Metrics:**
- ApproximateNumberOfMessages (queue depth)
- ApproximateNumberOfMessagesNotVisible
- NumberOfMessagesSent
- NumberOfMessagesReceived

**DynamoDB Metrics:**
- ReadCapacityUnits
- WriteCapacityUnits
- ThrottledRequests

**RDS Metrics:**
- CPUUtilization
- DatabaseConnections
- ReadLatency
- WriteLatency

### Alerting

**Critical Alerts:**
- High error rate (> 5% for 10 minutes)
- High latency (P95 > 5 seconds)
- Queue depth threshold (> 1000 messages)
- API down/unreachable
- DLQ growth (> 10 messages)

**Alert Channels:**
- CloudWatch Alarms → SNS → Email/Slack
- PagerDuty integration (for production)

### Dashboards

**CloudWatch Dashboard:**
- Real-time metrics
- Event ingestion rate
- Event delivery success rate
- Error rates by type
- Queue depth over time

---

## Performance Characteristics

### Latency Targets

- **Event Ingestion**: < 100ms (P95) from request to 202 response
- **Event Processing**: < 5 seconds (P95) from ingestion to workflow trigger
- **Event Query**: < 1 second for up to 1,000 events

### Throughput Targets

- **Launch**: 10,000 events per second
- **Scalable**: 100,000+ events per second (with Kinesis migration)

### Scalability

**Horizontal Scaling:**
- **API Lambda**: Auto-scales based on request rate (no limit)
- **Worker Lambda**: Auto-scales based on SQS queue depth
- **DynamoDB**: On-demand mode auto-scales
- **RDS**: Read replicas for high query volume

**Bottlenecks:**
- RDS connection pool (mitigated with connection pooling)
- Redis connection limits (mitigated with cluster mode)
- SQS throughput (can migrate to Kinesis for higher throughput)

---

## Deployment Environments

### Development

- **Infrastructure**: Single-AZ deployment
- **Instance Sizes**: Small (db.t3.micro, cache.t3.micro)
- **Monitoring**: Basic CloudWatch metrics
- **Cost**: Optimized for development

### Production

- **Infrastructure**: Multi-AZ deployment
- **Instance Sizes**: Medium+ (db.t3.medium, cache.t3.medium)
- **Monitoring**: Comprehensive dashboards and alerting
- **Backup**: Automated backups with point-in-time recovery
- **High Availability**: Multi-AZ RDS, Redis cluster mode

---

## Future Enhancements

### Phase 2 (Post-Launch)

- **Developer Testing UI**: Enhanced frontend with more features
- **Analytics Dashboard**: Comprehensive event analytics
- **SDK/Client Libraries**: Python, Node.js, Ruby SDKs
- **Event Transformation**: Advanced payload transformation

### Phase 3 (Future)

- **Kinesis Migration**: Higher throughput message queue
- **Multi-Region Deployment**: Global event ingestion
- **Event Replay**: Replay events from history
- **Advanced Matching**: Machine learning-based event matching
- **Event Streaming**: Real-time event streaming API

---

## Summary

The Zapier Triggers API is a production-ready, serverless event-driven system that:

1. **Accepts events** via REST API with authentication and rate limiting
2. **Stores events** in DynamoDB and queues them in SQS
3. **Processes events** asynchronously via Worker Lambda
4. **Matches events** to subscriptions using flexible matching logic
5. **Delivers webhooks** to subscription URLs with full retry logic and error handling
6. **Tracks status** of all events for audit and debugging

### Webhook Implementation Status

✅ **Fully Implemented and Operational**

- **Webhook Service**: Complete implementation in `app/services/webhook_service.py`
- **Subscription Management**: Subscriptions stored in RDS with `webhook_url` field
- **Delivery Logic**: HTTP POST with JSON array payload format (Zapier-compatible)
- **Retry Mechanism**: Exponential backoff with configurable max retries (default: 5)
- **Error Handling**: Comprehensive handling of 4xx, 5xx, timeouts, and network errors
- **Status Tracking**: Event status updated in DynamoDB (delivered/failed/unmatched)
- **410 Gone Handling**: Automatic subscription deactivation on 410 response
- **Testing Support**: Works with webhook.site, RequestBin, and custom endpoints
- **Production Ready**: Supports Zapier webhook URLs and custom application endpoints

The architecture is designed for:
- **High Availability**: Serverless, auto-scaling components
- **Reliability**: Durable storage, retry logic, DLQ
- **Performance**: Sub-100ms API response times
- **Scalability**: Handles high event volumes (10K+ events/second)
- **Observability**: Comprehensive logging and metrics
- **Security**: VPC networking, encryption, customer isolation

The system is fully deployed on AWS with Infrastructure as Code (Terraform + SAM), making it easy to deploy, update, and maintain.

