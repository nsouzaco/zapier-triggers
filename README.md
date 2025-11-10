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
- **Storage**: DynamoDB (events), RDS PostgreSQL (subscriptions), ElastiCache Redis (caching)
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
   docker-compose up -d
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

## Documentation

- **API Documentation**: Available at `/docs` when running the server
- **Architecture**: See `memory-bank/systemPatterns.md`
- **Technical Context**: See `memory-bank/techContext.md`
- **Tasks**: See `tasks.md` for development roadmap

## License

[To be determined]

