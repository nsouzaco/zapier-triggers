"""Operator endpoints for dashboard (no authentication required)."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.event_storage import event_storage
from app.services.customer_service import customer_service
from app.services.subscription_service import subscription_service
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/operators", tags=["operators"])


class SystemHealthResponse(BaseModel):
    status: str
    total_events: int
    events_today: int
    events_delivered_today: int
    events_failed_today: int
    success_rate: float
    queue_depth: Optional[int] = None


class EventSummaryResponse(BaseModel):
    event_id: str
    customer_id: str
    status: str
    timestamp: str
    event_type: Optional[str] = None


class EventsResponse(BaseModel):
    events: list[EventSummaryResponse]
    total: int
    has_more: bool


@router.get("/system-health", response_model=SystemHealthResponse)
async def get_system_health():
    """Get overall system health metrics."""
    try:
        # Get events from last 24 hours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        # Query all events (no customer filter)
        all_events = await event_storage.query_all_events(
            start_time=start_time,
            end_time=end_time,
            limit=10000,  # Large limit to get all events
        )
        
        # Calculate metrics
        total_events = len(all_events)
        events_delivered = sum(1 for e in all_events if e.get("status") == "delivered")
        events_failed = sum(1 for e in all_events if e.get("status") == "failed")
        
        # Calculate success rate
        processed_events = events_delivered + events_failed
        success_rate = (events_delivered / processed_events * 100) if processed_events > 0 else 0.0
        
        # Determine status
        if success_rate >= 95:
            status = "healthy"
        elif success_rate >= 90:
            status = "degraded"
        else:
            status = "unhealthy"
        
        # Get total events count (approximate)
        total_all_events = await event_storage.count_all_events()
        
        return SystemHealthResponse(
            status=status,
            total_events=total_all_events,
            events_today=total_events,
            events_delivered_today=events_delivered,
            events_failed_today=events_failed,
            success_rate=round(success_rate, 2),
            queue_depth=None,  # TODO: Get from SQS
        )
    except Exception as e:
        logger.error(f"Error getting system health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events", response_model=EventsResponse)
async def get_all_events(
    status: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
):
    """Get all events across all customers."""
    try:
        # Query all events (no customer filter)
        events = await event_storage.query_all_events(
            status=status,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
        
        # Convert to response format
        event_summaries = []
        for event in events:
            payload = event.get("payload", {})
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            
            event_summaries.append(
                EventSummaryResponse(
                    event_id=event.get("event_id", ""),
                    customer_id=event.get("customer_id", ""),
                    status=event.get("status", "pending"),
                    timestamp=event.get("timestamp", datetime.utcnow().isoformat()),
                    event_type=payload.get("event_type") if isinstance(payload, dict) else None,
                )
            )
        
        return EventsResponse(
            events=event_summaries,
            total=len(event_summaries),
            has_more=False,  # TODO: Implement pagination
        )
    except Exception as e:
        logger.error(f"Error getting events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customers")
async def get_all_customers():
    """Get list of all customers."""
    try:
        customers = customer_service.list_customers()
        return {
            "customers": [
                {
                    "customer_id": str(c.customer_id),
                    "name": c.name,
                    "email": c.email,
                    "status": c.status,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in customers
            ],
            "total": len(customers),
        }
    except Exception as e:
        logger.error(f"Error getting customers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/subscriptions")
async def get_all_subscriptions():
    """Get list of all subscriptions."""
    try:
        subscriptions = await subscription_service.get_all_subscriptions()
        return {
            "subscriptions": [
                {
                    "workflow_id": str(s.workflow_id),
                    "customer_id": str(s.customer_id),
                    "event_selector": s.event_selector,
                    "webhook_url": s.webhook_url,
                    "status": s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in subscriptions
            ],
            "total": len(subscriptions),
        }
    except Exception as e:
        logger.error(f"Error getting subscriptions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

