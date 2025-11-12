"""API endpoints for event ingestion."""

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import get_settings
from app.core.auth import get_customer_id_from_api_key
from app.core.idempotency import get_idempotency_key, idempotency_handler
from app.models.events import ErrorResponse, EventRequest, EventResponse
from app.services.event_storage import event_storage
from app.services.queue_service import queue_service
from app.utils.logging import get_logger

settings = get_settings()

logger = get_logger(__name__)

router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Submit Event",
    description="Submit an event to trigger Zapier workflows. Returns immediately with event ID.",
)
async def submit_event(
    request: EventRequest,
    customer_id: str = Depends(get_customer_id_from_api_key),
    idempotency_key: str = Depends(get_idempotency_key),
):
    """
    Submit an event for processing.

    This endpoint accepts events and immediately returns a 202 Accepted response
    with an event ID. The event is processed asynchronously.

    Args:
        request: Event request with payload
        customer_id: Customer ID from authentication
        idempotency_key: Optional idempotency key from header
        http_request: FastAPI request object

    Returns:
        EventResponse with event_id and status

    Raises:
        HTTPException: If validation fails or processing error occurs
    """
    try:
        # Check idempotency key if provided
        if idempotency_key:
            cached_response = await idempotency_handler.get_cached_response(idempotency_key)
            if cached_response:
                logger.info(f"Returning cached response for idempotency key: {idempotency_key[:10]}...")
                # Return the cached response directly
                return EventResponse(**cached_response.get("response", cached_response))

        # Generate event ID
        event_id = str(uuid4())

        # Store event in DynamoDB (or local storage in development)
        stored = await event_storage.store_event(
            customer_id=customer_id,
            event_id=event_id,
            payload=request.payload,
            status="pending",
        )
        if not stored:
            logger.debug(f"Event not stored in DynamoDB (development mode): {event_id}")

        # Enqueue event to SQS (or local queue in development)
        if queue_service.sqs_client and settings.sqs_event_queue_url:
            enqueued = await queue_service.enqueue_event(
                customer_id=customer_id,
                event_id=event_id,
                payload=request.payload,
            )
            if not enqueued:
                logger.error(f"Failed to enqueue event to SQS: {event_id}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process event. Please try again.",
                )
        else:
            # Local development mode - just log the event
            enqueued = await queue_service.enqueue_event_local(
                customer_id=customer_id,
                event_id=event_id,
                payload=request.payload,
            )
            logger.info(f"Event enqueued locally (development mode): {event_id}")

        # Create response
        response = EventResponse(
            event_id=event_id,
            status="accepted",
            message="Event accepted for processing",
            timestamp=datetime.utcnow(),
        )

        # Cache response if idempotency key provided
        if idempotency_key:
            await idempotency_handler.cache_response(
                idempotency_key=idempotency_key,
                event_id=event_id,
                response_data=response.model_dump(),
            )

        logger.info(f"Event submitted successfully: {event_id} for customer {customer_id}")
        return response

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error processing event: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again later.",
        )

