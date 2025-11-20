"""API endpoints for event retrieval."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.auth import get_customer_id_from_api_key
from app.models.events import ErrorResponse, EventFilter, EventItem, InboxResponse
from app.services.event_storage import event_storage
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get(
    "",
    response_model=InboxResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Retrieve Events",
    description="Retrieve events for the authenticated customer with optional filtering.",
)
async def get_events(
    customer_id: str = Depends(get_customer_id_from_api_key),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp"),
    end_time: Optional[datetime] = Query(None, description="End timestamp"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """
    Retrieve events for the authenticated customer.

    Args:
        customer_id: Customer ID from authentication
        event_type: Optional filter by event type
        status_filter: Optional filter by status
        start_time: Optional start timestamp
        end_time: Optional end timestamp
        limit: Maximum number of events to return
        cursor: Pagination cursor

    Returns:
        InboxResponse with list of events

    Raises:
        HTTPException: If query fails
    """
    try:
        # Query events from DynamoDB (or local storage in development)
        events = await event_storage.query_events(
            customer_id=customer_id,
            event_type=event_type,
            status=status_filter,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        # Convert to EventItem models
        event_items = []
        for e in events:
            try:
                payload = e.get("payload", {})
                if isinstance(payload, str):
                    import json
                    payload = json.loads(payload)

                event_item = EventItem(
                    event_id=e.get("event_id", ""),
                    customer_id=e.get("customer_id", customer_id),
                    payload=payload,
                    status=e.get("status", "pending"),
                    timestamp=datetime.fromisoformat(e.get("timestamp", datetime.utcnow().isoformat())),
                    delivery_attempts=e.get("delivery_attempts"),
                    last_delivery_timestamp=(
                        datetime.fromisoformat(e.get("last_delivery_timestamp"))
                        if e.get("last_delivery_timestamp")
                        else None
                    ),
                )
                event_items.append(event_item)
            except Exception as e:
                logger.warning(f"Error converting event to EventItem: {e}")
                continue

        # Determine if there are more events (if we got exactly the limit, there might be more)
        has_more = len(events) == limit

        logger.info(f"Retrieved {len(event_items)} events for customer {customer_id}")

        return InboxResponse(
            events=event_items,
            total=len(event_items),
            cursor=None,  # TODO: Implement cursor-based pagination
            has_more=has_more,
        )

    except Exception as e:
        logger.error(f"Error retrieving events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving events.",
        )


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        404: {"model": ErrorResponse, "description": "Event not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Delete Event",
    description="Delete an event by ID. Only the event owner can delete their events.",
)
async def delete_event(
    event_id: str,
    customer_id: str = Depends(get_customer_id_from_api_key),
):
    """
    Delete an event.

    This endpoint allows customers to delete their own events. The event must
    belong to the authenticated customer. This is useful for:
    - Compliance (GDPR/CCPA right to be forgotten)
    - Storage cost management
    - Testing and debugging
    - Marking events as processed

    Args:
        event_id: Event identifier
        customer_id: Customer ID from authentication

    Returns:
        204 No Content on success

    Raises:
        HTTPException: If event not found or deletion fails
    """
    try:
        deleted = await event_storage.delete_event(
            customer_id=customer_id,
            event_id=event_id,
        )

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found or you don't have permission to delete it.",
            )

        logger.info(f"Event deleted successfully: {event_id} by customer {customer_id}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the event.",
        )

