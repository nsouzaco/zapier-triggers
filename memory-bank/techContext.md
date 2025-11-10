# Technical Context: Zapier Triggers API

## Technology Stack

### Core Framework
- **API Framework**: FastAPI (Python)
- **Deployment**: AWS Lambda (serverless) or ECS Fargate (containers)
- **Language**: Python 3.x

### AWS Services

#### Compute
- **API Layer**: AWS Lambda or ECS Fargate
- **Processing Workers**: AWS Lambda or ECS
- **Auto-Scaling**: AWS Auto Scaling Groups with CloudWatch metrics

#### Messaging
- **Message Queue**: AWS SQS (MVP), AWS Kinesis (future option)
- **Dead-Letter Queue**: AWS SQS DLQ

#### Storage
- **Event Database**: AWS DynamoDB (NoSQL)
- **Subscription Database**: Amazon RDS PostgreSQL
- **Cache**: Amazon ElastiCache Redis

#### Infrastructure
- **Load Balancing**: AWS Application Load Balancer (ALB)
- **Monitoring**: AWS CloudWatch
- **Encryption**: AWS KMS
- **Networking**: AWS VPC

### Data Storage Schemas

#### DynamoDB Event Schema
```
Partition Key: customer_id
Sort Key: event_id (or timestamp)
Attributes:
  - payload (JSON)
  - timestamp (ISO 8601)
  - status (pending/delivered/failed/dead-lettered)
  - delivery_attempts (number)
  - last_delivery_timestamp (ISO 8601)
  - retry_count (number)
  - metadata (JSON)
TTL: configurable retention period (default 90 days)
```

#### RDS PostgreSQL Subscription Schema
```
Table: subscriptions
Columns:
  - workflow_id (UUID, primary key)
  - customer_id (UUID, indexed)
  - event_selector (JSONB, indexed)
  - webhook_url (TEXT)
  - status (active/disabled)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)
Indexes:
  - customer_id (for subscription lookup)
  - event_selector (for matching queries)
```

#### Redis Cache Schema
```
Rate Limiting:
  Key: rate_limit:{api_key}:{window}
  Value: count
  TTL: rate limit window duration

Idempotency:
  Key: idempotency:{idempotency_key}
  Value: event_id
  TTL: 24 hours
```

## Development Setup

### Prerequisites
- Python 3.9+
- AWS CLI configured
- Docker (for local development)
- Terraform or AWS CDK (for infrastructure)

### Local Development
- FastAPI development server
- Local DynamoDB (DynamoDB Local)
- Local PostgreSQL (Docker)
- Local Redis (Docker)
- Mock SQS (localstack or moto)

### Testing
- Unit tests: pytest
- Integration tests: pytest with testcontainers
- Load testing: Locust or k6
- API testing: pytest-httpx

## Deployment Architecture

### Environment Strategy
- **Development**: Isolated AWS account/environment
- **Staging**: Production-like environment for testing
- **Production**: Multi-AZ deployment with high availability

### Infrastructure as Code
- **Option 1**: Terraform
- **Option 2**: AWS CDK (Python)
- **Option 3**: Serverless Framework

### CI/CD Pipeline
- **Source Control**: Git (GitHub/GitLab)
- **Build**: GitHub Actions / GitLab CI / AWS CodePipeline
- **Deploy**: Automated deployment to staging, manual approval for production
- **Testing**: Automated test suite in CI pipeline

## Performance Requirements

### Latency Targets
- **Ingestion**: < 100ms (P95) from request to 202 response
- **Processing**: < 5 seconds (P95) from ingestion to workflow trigger
- **Query**: < 1 second for up to 1,000 events

### Throughput Targets
- **Launch**: 10,000 events per second
- **Scalable**: 100,000+ events per second

### Reliability Targets
- **Uptime**: 99.9% availability
- **Data Loss**: Zero data loss
- **Delivery**: At-least-once semantics

## Security Requirements

### Authentication
- API key authentication (Bearer token)
- API keys tied to customer accounts
- Support for API key rotation

### Authorization
- Customer data isolation
- Role-based access control (RBAC) for internal tools
- OAuth 2.0 for testing UI and dashboards

### Encryption
- **In Transit**: HTTPS/TLS 1.2+
- **At Rest**: AWS KMS encryption
- **Database**: Encrypted storage with KMS keys

### Compliance
- **GDPR**: Data subject access requests, right to be forgotten
- **CCPA**: Data deletion capabilities
- **SOC 2**: Security and availability audit standards
- **Audit Logging**: All API access logged with timestamps

## Monitoring and Observability

### Metrics (CloudWatch)
- Event ingestion rate
- Event delivery success rate
- API latency (P50, P95, P99)
- Queue depth
- Error rates by type
- Rate limit usage

### Logging
- Structured JSON logging
- Request/response logging
- Error logging with stack traces
- Audit logging for compliance

### Alerting
- High error rate (> 5% for 10 minutes)
- High latency (P95 > 5 seconds)
- Queue depth threshold
- API down/unreachable
- DLQ growth

### Dashboards
- Real-time metrics dashboard
- Historical analytics
- Per-customer metrics
- System health overview

## Dependencies

### External Dependencies
- **Zapier Workflow Execution Engine**: Webhook endpoint for event delivery
- **AWS Services**: Lambda, SQS, DynamoDB, RDS, ElastiCache, CloudWatch, KMS

### Internal Dependencies
- Customer database for API key validation
- Zapier authentication system (OAuth) for testing UI

### Third-Party Libraries
- FastAPI: Web framework
- Pydantic: Data validation
- boto3: AWS SDK
- SQLAlchemy: ORM for PostgreSQL
- redis-py: Redis client
- httpx: HTTP client for webhooks

## Technical Constraints

### AWS Service Limits
- SQS message size: 256 KB
- DynamoDB item size: 400 KB
- Lambda execution time: 15 minutes max
- API Gateway payload: 10 MB max

### Design Constraints
- Event payload max size: 1 MB
- Rate limit default: 1,000 events/second per customer
- Idempotency window: 24 hours
- Event retention: 90 days default (configurable)

## Development Tools

### Code Quality
- **Linting**: black, flake8, mypy
- **Formatting**: black
- **Type Checking**: mypy
- **Testing**: pytest with coverage

### Documentation
- **API Docs**: OpenAPI/Swagger (auto-generated from FastAPI)
- **Code Docs**: Sphinx or MkDocs
- **Architecture**: Diagrams in Markdown or Mermaid

### Version Control
- Git with conventional commits
- Branch strategy: main, develop, feature branches
- Code review required for all changes

