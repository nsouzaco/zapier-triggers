# Zapier Triggers API

A unified, event-driven API for triggering Zapier workflows in real-time.

## Overview

The Zapier Triggers API provides a public, reliable, and developer-friendly RESTful interface for any system to send events into Zapier, triggering workflows instantly and reliably.

## Features

- **Unified Event Ingestion**: Single REST endpoint (`POST /events`) for event submission
- **Real-Time Processing**: Sub-100ms latency for event acknowledgment
- **Dynamic Routing**: Automatic event routing based on payload content and subscriptions
- **Durable Storage**: All events persisted for audit and replay
- **Reliable Delivery**: At-least-once delivery with automatic retry logic
- **Rate Limiting**: Per-customer rate limiting with configurable quotas
- **Idempotency**: Support for idempotency keys to prevent duplicate events

## Architecture

The system is built on AWS-native services with an asynchronous, event-driven architecture:

- **API Layer**: FastAPI on AWS Lambda or ECS Fargate
- **Message Queue**: AWS SQS for durable event storage
- **Processing Workers**: AWS Lambda or ECS for event processing
- **Storage**: DynamoDB (events), **AWS RDS PostgreSQL** (subscriptions & API keys), ElastiCache Redis (caching)
- **Note**: All database operations use **AWS RDS only** - local database is not used
- **Delivery**: Webhook callbacks to Zapier workflow execution engine

## Development Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- AWS CLI (for AWS services)
- PostgreSQL client (optional, for direct database access)

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd zapier-triggers-api
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Start local services**
   ```bash
   docker-compose up -d redis dynamodb-local
   # Note: PostgreSQL service is commented out - we use AWS RDS only
   ```

6. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

7. **Start the development server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

The API will be available at `http://localhost:8000`

API documentation (Swagger UI) will be available at `http://localhost:8000/docs`

## Project Structure

```
zapier-triggers-api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── api/                 # API routes
│   │   ├── __init__.py
│   │   ├── events.py        # POST /events endpoint
│   │   └── inbox.py         # GET /inbox endpoint
│   ├── core/                # Core business logic
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication middleware
│   │   ├── rate_limiter.py  # Rate limiting logic
│   │   ├── idempotency.py   # Idempotency handling
│   │   └── matching.py      # Event matching logic
│   ├── models/              # Pydantic models
│   │   ├── __init__.py
│   │   ├── events.py        # Event models
│   │   └── responses.py     # Response models
│   ├── services/            # Business logic services
│   │   ├── __init__.py
│   │   ├── event_service.py # Event ingestion service
│   │   ├── queue_service.py # Queue management
│   │   └── webhook_service.py # Webhook delivery
│   ├── workers/            # Background workers
│   │   ├── __init__.py
│   │   └── event_processor.py # Event processing worker
│   ├── database/           # Database models and migrations
│   │   ├── __init__.py
│   │   ├── models.py       # SQLAlchemy models
│   │   └── migrations/     # Alembic migrations
│   └── utils/             # Utility functions
│       ├── __init__.py
│       ├── logging.py     # Logging configuration
│       └── aws.py         # AWS service clients
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── memory-bank/           # Project documentation
├── docker-compose.yml     # Local development services
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_events.py
```

## Code Quality

```bash
# Format code
black app tests

# Lint code
flake8 app tests

# Type checking
mypy app
```

## AWS Credentials & Lambda VPC

### Lambda VPC Configuration

When deployed to Lambda in a VPC, the application automatically uses IAM role credentials via the credential chain:
1. Environment variables (none set in Lambda)
2. `~/.aws/credentials` (doesn't exist in Lambda)
3. IMDS via STS VPC endpoint → IAM role credentials

**Important**: Do NOT set `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY` in Lambda environment variables. The code will automatically use the IAM role.

### Local Development

For local development with explicit credentials, set the `IS_LOCAL_DEV` environment variable:

```bash
export IS_LOCAL_DEV=true
# Or in .env file:
IS_LOCAL_DEV=true
```

This allows the code to use explicit credentials from your `.env` file or AWS credentials file for local testing.

### Troubleshooting

If you encounter `InvalidClientTokenId` or `UnrecognizedClientException` errors:
- Ensure Lambda is in a VPC with STS VPC endpoint configured
- Verify security groups allow traffic to VPC endpoints
- Check IAM role has correct permissions
- See `LAMBDA_VPC_CREDENTIAL_FIX.md` for detailed troubleshooting

## Documentation

- **API Documentation**: Available at `/docs` when running the server
- **Architecture**: See `memory-bank/systemPatterns.md`
- **Technical Context**: See `memory-bank/techContext.md`
- **Tasks**: See `tasks.md` for development roadmap
- **Credential Fix**: See `CREDENTIAL_FIX_IMPLEMENTED.md` for Lambda VPC credential details

## License

[To be determined]

