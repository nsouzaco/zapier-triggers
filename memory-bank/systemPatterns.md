# System Patterns: Zapier Triggers API

## Architecture Overview

The Zapier Triggers API employs a fully asynchronous, event-driven architecture designed for high scalability and fault tolerance. The system is built on AWS-native services and follows industry best practices.

## Architectural Layers

### 1. Ingestion Layer
- **Purpose**: Receives and validates incoming events, returns immediate acknowledgment
- **Components**: FastAPI on AWS Lambda or ECS Fargate
- **Key Pattern**: Stateless, horizontally scalable API servers
- **Responsibilities**:
  - JSON schema validation
  - API key authentication
  - Rate limiting checks
  - Event ID generation
  - Queue enqueueing
  - HTTP 202 response within 100ms

### 2. Queue Layer
- **Purpose**: Durably stores events, acts as buffer for traffic spikes
- **Components**: AWS SQS (MVP) or Kinesis (future)
- **Key Pattern**: Decoupled, asynchronous message queue
- **Responsibilities**:
  - Durable message storage
  - At-least-once delivery guarantees
  - Automatic message retention (14 days)
  - Dead-letter queue integration

### 3. Processing Layer
- **Purpose**: Consumes events, matches against subscriptions, triggers workflows
- **Components**: AWS Lambda or ECS workers
- **Key Pattern**: Stateless workers with auto-scaling
- **Responsibilities**:
  - Event consumption from queue
  - Subscription lookup and matching
  - Event storage in DynamoDB
  - Webhook delivery to workflow engine
  - Retry logic with exponential backoff

### 4. Storage Layer
- **Purpose**: Persists events and subscription metadata
- **Components**: 
  - DynamoDB (events)
  - RDS PostgreSQL (subscriptions)
  - ElastiCache Redis (rate limiting, idempotency)
- **Key Pattern**: Multi-database architecture optimized for different access patterns
- **Responsibilities**:
  - Event persistence with full payload
  - Subscription metadata storage
  - Rate limit tracking
  - Idempotency key caching

### 5. Delivery Layer
- **Purpose**: Sends webhook callbacks to workflow execution engine
- **Components**: HTTP client with retry logic
- **Key Pattern**: REST Hook subscription model aligned with Zapier patterns
- **Responsibilities**:
  - Webhook delivery with exponential backoff
  - Batch event delivery (array-based)
  - Subscription lifecycle management
  - Dead-letter queue for failed deliveries

## Key Design Patterns

### Asynchronous Processing Pattern
- **Principle**: Decouple ingestion from processing
- **Implementation**: API enqueues to SQS, returns 202 immediately
- **Benefit**: API remains fast and responsive regardless of downstream load

### Event-Driven Architecture
- **Principle**: Components communicate via events/messages
- **Implementation**: SQS queue as central event bus
- **Benefit**: Loose coupling, independent scaling, fault tolerance

### Stateless Services
- **Principle**: All services are stateless and horizontally scalable
- **Implementation**: No shared state between instances, all state in databases
- **Benefit**: Unlimited horizontal scaling, no coordination overhead

### At-Least-Once Delivery
- **Principle**: Guarantee events are delivered, even if duplicates occur
- **Implementation**: SQS at-least-once semantics, idempotency keys
- **Benefit**: No data loss, idempotent processing handles duplicates

### Subscription-Based Routing
- **Principle**: Dynamic routing based on event payload and customer subscriptions
- **Implementation**: Workers query subscriptions, apply matching logic (JSONPath, event_type)
- **Benefit**: Flexible routing without customer-managed endpoints

### Exponential Backoff Retry
- **Principle**: Retry failed deliveries with increasing delays
- **Implementation**: Initial retry within seconds, increasing up to 24 hours
- **Benefit**: Handles transient failures, avoids overwhelming downstream systems

### Dead-Letter Queue Pattern
- **Principle**: Isolate permanently failed events for manual inspection
- **Implementation**: Events moved to DLQ after max retry attempts
- **Benefit**: Prevents queue blocking, enables failure analysis

## Data Flow Patterns

### Event Ingestion Flow
```
External System → API Layer → Validation → Authentication → Rate Limit Check → 
Queue Enqueue → HTTP 202 Response
```

### Event Processing Flow
```
SQS Queue → Worker → Subscription Lookup → Event Matching → 
DynamoDB Storage → Webhook Delivery → Status Update → Queue Delete
```

### Event Retrieval Flow
```
Customer → API Layer → Authentication → DynamoDB Query → 
Filtering → Pagination → Response
```

## Component Relationships

### API Layer Dependencies
- ElastiCache Redis (rate limiting, idempotency)
- SQS (event queue)
- Customer Database (authentication)

### Worker Dependencies
- SQS (event consumption)
- RDS PostgreSQL (subscription lookup)
- DynamoDB (event storage)
- Workflow Execution Engine (webhook delivery)

### Storage Dependencies
- DynamoDB (events) - independent
- RDS PostgreSQL (subscriptions) - independent
- ElastiCache Redis (caching) - independent

## Scaling Patterns

### Horizontal Scaling
- **API Layer**: Stateless, scales based on request rate
- **Workers**: Scale based on SQS queue depth
- **Databases**: Auto-scaling based on capacity utilization

### Auto-Scaling Triggers
- API: CloudWatch alarms on latency/error rate
- Workers: SQS queue depth metrics
- DynamoDB: On-demand mode auto-scales
- RDS: Read replicas for high query volume

## Resilience Patterns

### Multi-AZ Deployment
- All components deployed across multiple availability zones
- Automatic failover for database services
- Load balancer routes to healthy instances

### Retry and Recovery
- Message visibility timeout prevents duplicate processing
- Exponential backoff handles transient failures
- Dead-letter queue captures permanent failures

### Data Durability
- Events persisted to DynamoDB before acknowledgment
- SQS provides built-in replication
- Database backups and point-in-time recovery

## Integration Patterns

### Zapier Webhook Integration
- **Pattern**: REST Hook subscription model
- **Lifecycle**: Subscribe on Zap activation, unsubscribe on deactivation
- **Delivery**: Batch array-based webhook payloads
- **Cleanup**: Auto-unsubscribe on 410 (Gone) response

### API Key Authentication
- **Pattern**: Bearer token in Authorization header
- **Validation**: API key → customer_id lookup
- **Isolation**: Strict customer data segregation

### Idempotency Pattern
- **Key**: Idempotency-Key header
- **Storage**: Redis cache with TTL
- **Behavior**: Return cached response for duplicate keys

