"""Demo Backend for Zapier Triggers API.

This is a separate FastAPI application that orchestrates demo workflows by:
1. Receiving input from the frontend
2. Running agent logic to decide whether to trigger an event
3. Calling the production Triggers API to submit the event
4. Independently calling Resend API to send a demo email
5. Returning complete status to the frontend
"""

import logging
import os
from datetime import datetime
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Environment variables
TRIGGERS_API_URL = os.getenv("TRIGGERS_API_URL", "").rstrip("/")
TRIGGERS_API_KEY = os.getenv("TRIGGERS_API_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
DEMO_RECIPIENT_EMAIL = os.getenv("DEMO_RECIPIENT_EMAIL", "")
PORT = int(os.getenv("PORT", "8000"))

# Validate required environment variables
if not TRIGGERS_API_URL:
    logger.warning("TRIGGERS_API_URL not set")
if not TRIGGERS_API_KEY:
    logger.warning("TRIGGERS_API_KEY not set")
if not RESEND_API_KEY:
    logger.warning("RESEND_API_KEY not set")
if not DEMO_RECIPIENT_EMAIL:
    logger.warning("DEMO_RECIPIENT_EMAIL not set")

# Create FastAPI application
app = FastAPI(
    title="Zapier Triggers API Demo Backend",
    version="1.0.0",
    description="Demo orchestrator for Zapier Triggers API workflows",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic Models
class TriggerRequest(BaseModel):
    """Request model for demo trigger endpoint."""

    document_type: str = Field(..., description="Type of document/event")
    priority: str = Field(..., description="Priority level (high, normal, low)")
    description: str = Field(..., description="Event description")
    customer_email: str = Field(..., description="Customer email address")


class TriggerResponse(BaseModel):
    """Response model for successful trigger."""

    triggered: bool = Field(..., description="Whether event was triggered")
    reason: str = Field(..., description="Reason for trigger decision")
    event_id: Optional[str] = Field(None, description="Event ID from Triggers API")
    email_sent: bool = Field(False, description="Whether demo email was sent")
    recipient_email: Optional[str] = Field(None, description="Email recipient")
    message: str = Field(..., description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")


class EventStatusResponse(BaseModel):
    """Response model for event status check."""

    event_id: str = Field(..., description="Event ID")
    status: str = Field(..., description="Event status")
    payload: dict = Field(..., description="Event payload")
    timestamp: datetime = Field(..., description="Event timestamp")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Health status")
    environment: str = Field(default="demo", description="Environment name")


# Agent Logic
def should_trigger_event(document_type: str, priority: str, description: str) -> tuple[bool, str]:
    """
    Determines if an event should be triggered based on form data.

    Args:
        document_type: Type of document/event
        priority: Priority level
        description: Event description

    Returns:
        Tuple of (should_trigger: bool, reason: str)
    """
    urgent_keywords = ["angry", "urgent", "critical", "escalate", "emergency"]

    if priority.lower() == "high":
        return True, "Priority is high"

    if any(keyword in description.lower() for keyword in urgent_keywords):
        return True, "Description contains urgent keywords"

    return False, "Priority is normal and no urgent keywords detected"


# Triggers API Integration
def submit_event_to_triggers_api(payload: dict) -> dict:
    """
    Call the production Triggers API to submit an event.

    Args:
        payload: Event payload to submit

    Returns:
        Response dict with event_id and status

    Raises:
        Exception: If API call fails
    """
    if not TRIGGERS_API_URL or not TRIGGERS_API_KEY:
        raise ValueError("TRIGGERS_API_URL and TRIGGERS_API_KEY must be set")

    headers = {"Authorization": f"Bearer {TRIGGERS_API_KEY}", "Content-Type": "application/json"}
    url = f"{TRIGGERS_API_URL}/api/v1/events"

    logger.info(f"Submitting event to Triggers API: {url}")

    try:
        response = requests.post(
            url,
            json={"payload": payload},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Event submitted successfully: {result.get('event_id')}")
        return result
    except requests.exceptions.Timeout:
        logger.error("Triggers API request timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Triggers API request timed out",
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Triggers API request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to submit event to Triggers API: {str(e)}",
        )


def get_event_status(event_id: str) -> dict:
    """
    Fetch event status from Triggers API inbox.

    Args:
        event_id: Event ID to look up

    Returns:
        Event details including status

    Raises:
        ValueError: If event not found
        HTTPException: If API call fails
    """
    if not TRIGGERS_API_URL or not TRIGGERS_API_KEY:
        raise ValueError("TRIGGERS_API_URL and TRIGGERS_API_KEY must be set")

    headers = {"Authorization": f"Bearer {TRIGGERS_API_KEY}"}
    url = f"{TRIGGERS_API_URL}/api/v1/inbox"

    logger.info(f"Fetching event status from Triggers API: {url}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        events = data.get("events", [])
        for event in events:
            if event.get("event_id") == event_id:
                logger.info(f"Event {event_id} found with status: {event.get('status')}")
                return event

        logger.warning(f"Event {event_id} not found in inbox")
        raise ValueError(f"Event {event_id} not found")
    except requests.exceptions.Timeout:
        logger.error("Triggers API request timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Triggers API request timed out",
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Triggers API request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch event status: {str(e)}",
        )


# Resend Integration
def send_demo_email(event_id: str, form_data: dict, recipient: str) -> dict:
    """
    Send a demo email via Resend API to prove workflow execution.

    Args:
        event_id: Event ID that was submitted
        form_data: Original form data
        recipient: Email recipient

    Returns:
        Response dict with success status and message_id

    Raises:
        Exception: If API call fails
    """
    if not RESEND_API_KEY:
        raise ValueError("RESEND_API_KEY must be set")

    headers = {"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"}

    email_body = f"""
    <html>
    <body>
        <h2>Demo workflow triggered successfully!</h2>
        <p>
            <strong>Event ID:</strong> {event_id}<br>
            <strong>Type:</strong> {form_data.get('document_type')}<br>
            <strong>Priority:</strong> {form_data.get('priority')}<br>
            <strong>Description:</strong> {form_data.get('description')}<br>
            <strong>Customer Email:</strong> {form_data.get('customer_email')}
        </p>
        <p>This email was sent by the demo backend as proof of workflow execution.</p>
    </body>
    </html>
    """

    logger.info(f"Sending demo email to {recipient}")

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            json={
                "from": "Zapier Triggers <onboarding@resend.dev>",
                "to": recipient,
                "subject": f"[Demo] Event Triggered: {form_data.get('document_type')}",
                "html": email_body,
            },
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"Demo email sent successfully: {result.get('id')}")
        return result
    except requests.exceptions.Timeout:
        logger.error("Resend API request timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Resend API request timed out",
        )
    except requests.exceptions.RequestException as e:
        logger.error(f"Resend API request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send demo email: {str(e)}",
        )


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(status="healthy", environment="demo")


@app.post("/demo/trigger", response_model=TriggerResponse, status_code=status.HTTP_200_OK)
async def trigger_demo_workflow(request: TriggerRequest):
    """
    Orchestrate the entire demo workflow.

    This endpoint:
    1. Validates input
    2. Runs agent logic to decide if event should be triggered
    3. If triggered: calls Triggers API and sends demo email
    4. Returns complete status
    """
    logger.info(
        f"Demo trigger request received: document_type={request.document_type}, "
        f"priority={request.priority}"
    )

    # Run agent logic
    should_trigger, reason = should_trigger_event(
        request.document_type, request.priority, request.description
    )

    if not should_trigger:
        logger.info(f"Agent decided not to trigger: {reason}")
        return TriggerResponse(
            triggered=False,
            reason=reason,
            message=f"Event not triggered: {reason}",
        )

    # Agent decided to trigger - proceed with workflow
    logger.info(f"Agent decided to trigger: {reason}")

    # Prepare event payload
    event_payload = {
        "event_type": f"{request.document_type}.created",
        "document_type": request.document_type,
        "priority": request.priority,
        "description": request.description,
        "customer_email": request.customer_email,
    }

    # Submit event to Triggers API
    event_id = None
    try:
        triggers_response = submit_event_to_triggers_api(event_payload)
        event_id = triggers_response.get("event_id")
        logger.info(f"Event submitted to Triggers API: {event_id}")
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to submit event to Triggers API: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit event: {str(e)}",
        )

    # Send demo email (secondary action - don't fail if this fails)
    email_sent = False
    email_error = None
    if event_id:
        try:
            send_demo_email(event_id, request.dict(), DEMO_RECIPIENT_EMAIL)
            email_sent = True
            logger.info(f"Demo email sent successfully for event {event_id}")
        except HTTPException:
            # Don't fail the whole request if email fails
            logger.warning(f"Failed to send demo email for event {event_id}", exc_info=True)
            email_error = "Email sending failed but event was submitted"
        except Exception as e:
            logger.warning(f"Failed to send demo email for event {event_id}: {e}", exc_info=True)
            email_error = f"Email sending failed: {str(e)}"

    message = "Event submitted to Triggers API and demo email sent"
    if email_error:
        message += f" (Note: {email_error})"

    return TriggerResponse(
        triggered=True,
        reason=reason,
        event_id=event_id,
        email_sent=email_sent,
        recipient_email=DEMO_RECIPIENT_EMAIL if email_sent else None,
        message=message,
    )


@app.get("/demo/status/{event_id}", response_model=EventStatusResponse)
async def get_event_status_endpoint(event_id: str):
    """
    Check event processing status in the Triggers API.

    Args:
        event_id: Event ID to check

    Returns:
        Event status and details
    """
    logger.info(f"Checking status for event: {event_id}")

    try:
        event = get_event_status(event_id)

        # Parse timestamp if it's a string
        timestamp = event.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.utcnow()

        return EventStatusResponse(
            event_id=event.get("event_id", event_id),
            status=event.get("status", "unknown"),
            payload=event.get("payload", {}),
            timestamp=timestamp,
        )
    except ValueError as e:
        logger.warning(f"Event not found: {event_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Failed to get event status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get event status: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)

