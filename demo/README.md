# Zapier Triggers API Demo Backend

This is a separate FastAPI application that orchestrates demo workflows by calling the production Triggers API and integrating with third-party services.

## Overview

The demo backend acts as an orchestrator that:
1. Receives input from the frontend
2. Runs agent logic to decide whether to trigger an event
3. Calls the production Triggers API to submit the event
4. Independently calls Resend API to send a demo email as proof of workflow completion
5. Returns complete status to the frontend showing both actions succeeded

## Architecture

```
Frontend → Demo Backend → Triggers API (event submission)
                      ↓
                   Resend API (demo email)
```

The demo backend is a **consumer** of the Triggers API, demonstrating how to use it in a real-world scenario. It does not modify or extend the production API.

## Setup

### Prerequisites

- Python 3.11+
- Access to deployed Triggers API
- Resend API key
- API key for the Triggers API

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Required environment variables:

- `TRIGGERS_API_URL` - Base URL of the deployed Triggers API (e.g., `https://xxx.execute-api.us-east-1.amazonaws.com/Prod`)
- `TRIGGERS_API_KEY` - API key for authenticating with the Triggers API
- `RESEND_API_KEY` - API key for Resend email service
- `DEMO_RECIPIENT_EMAIL` - Email address to send demo emails to
- `PORT` - Port to run on (default: 8000)

### Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables (see above)

3. Run the application:

```bash
python app.py
```

Or with uvicorn directly:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### POST /demo/trigger

Orchestrates the entire demo workflow.

**Request Body:**
```json
{
  "document_type": "support_ticket",
  "priority": "high",
  "description": "Customer is very angry about order",
  "customer_email": "customer@example.com"
}
```

**Success Response (200):**
```json
{
  "triggered": true,
  "reason": "Priority is high",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "email_sent": true,
  "recipient_email": "demo@example.com",
  "message": "Event submitted to Triggers API and demo email sent",
  "timestamp": "2024-01-15T10:30:05Z"
}
```

**Not Triggered Response (200):**
```json
{
  "triggered": false,
  "reason": "Priority is normal and no urgent keywords detected",
  "timestamp": "2024-01-15T10:30:05Z"
}
```

### GET /demo/status/{event_id}

Checks event processing status in the Triggers API.

**Response:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "delivered",
  "payload": {
    "document_type": "support_ticket",
    "priority": "high",
    "description": "Customer is very angry about order"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "environment": "demo"
}
```

## Agent Logic

The demo backend includes simple agent logic that determines whether to trigger an event:

- **Triggers if:**
  - Priority is "high", OR
  - Description contains urgent keywords: "angry", "urgent", "critical", "escalate", "emergency"

- **Does not trigger if:**
  - Priority is normal/low AND no urgent keywords are detected

## Error Handling

- **400 Bad Request**: Invalid input data
- **404 Not Found**: Event ID not found in Triggers API
- **500 Internal Server Error**: Server-side errors
- **502 Bad Gateway**: Triggers API or Resend API unavailable
- **504 Gateway Timeout**: API request timeout

If the Triggers API call fails, the request fails. If the email send fails after successful event submission, the request still succeeds (email is secondary).

## Deployment

### Railway

The included `Dockerfile` is configured for Railway deployment:

1. Connect your repository to Railway
2. Set environment variables in Railway dashboard
3. Railway will automatically build and deploy using the Dockerfile

### Docker

Build and run locally:

```bash
docker build -t demo-backend .
docker run -p 8000:8000 --env-file .env demo-backend
```

## Logging

The application logs:
- Demo trigger requests (what was submitted, agent decision)
- Triggers API calls (success/failure)
- Resend API calls (success/failure)
- All errors with context

Logs are output to stdout in JSON format for easy parsing.

## CORS

CORS is enabled to allow frontend requests from different origins. For production, you may want to restrict `allow_origins` to specific domains.

## Code Style

- Type hints throughout
- FastAPI best practices
- Pydantic models for request/response validation
- Focused, testable functions
- Docstrings on all functions

## Testing

Example curl commands:

```bash
# Trigger demo workflow
curl -X POST http://localhost:8000/demo/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "document_type": "support_ticket",
    "priority": "high",
    "description": "Customer is very angry",
    "customer_email": "customer@example.com"
  }'

# Check event status
curl http://localhost:8000/demo/status/{event_id}

# Health check
curl http://localhost:8000/health
```

## Notes

- The demo backend is stateless and does not require a database
- It does not modify the production Triggers API (`/app/`)
- Email sending is independent of event submission (demonstrates side effects)
- The agent logic is intentionally simple for demo purposes

