"""Pydantic models for event requests and responses."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class EventRequest(BaseModel):
    """Request model for event submission."""

    payload: Dict[str, Any] = Field(
        ...,
        description="Event payload as JSON object",
        examples=[{"event_type": "order.created", "order_id": "12345", "amount": 99.99}],
    )

    @field_validator("payload")
    @classmethod
    def validate_payload_size(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate payload size (max 1MB)."""
        import json

        payload_str = json.dumps(v)
        size_mb = len(payload_str.encode("utf-8")) / (1024 * 1024)
        if size_mb > 1:
            raise ValueError(f"Payload size ({size_mb:.2f}MB) exceeds maximum of 1MB")
        return v


class EventResponse(BaseModel):
    """Response model for event submission."""

    event_id: str = Field(..., description="Unique event identifier")
    status: str = Field(default="accepted", description="Event status")
    message: str = Field(default="Event accepted for processing", description="Response message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class EventFilter(BaseModel):
    """Filter model for event retrieval."""

    event_type: Optional[str] = Field(None, description="Filter by event type")
    status: Optional[str] = Field(None, description="Filter by status (pending, delivered, failed)")
    start_time: Optional[datetime] = Field(None, description="Start timestamp for filtering")
    end_time: Optional[datetime] = Field(None, description="End timestamp for filtering")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum number of events to return")
    cursor: Optional[str] = Field(None, description="Pagination cursor")


class EventItem(BaseModel):
    """Model for individual event in inbox response."""

    event_id: str = Field(..., description="Unique event identifier")
    customer_id: str = Field(..., description="Customer identifier")
    payload: Dict[str, Any] = Field(..., description="Event payload")
    status: str = Field(..., description="Event status")
    timestamp: datetime = Field(..., description="Event timestamp")
    delivery_attempts: Optional[int] = Field(None, description="Number of delivery attempts")
    last_delivery_timestamp: Optional[datetime] = Field(None, description="Last delivery attempt timestamp")


class InboxResponse(BaseModel):
    """Response model for event inbox retrieval."""

    events: list[EventItem] = Field(..., description="List of events")
    total: int = Field(..., description="Total number of events matching filter")
    cursor: Optional[str] = Field(None, description="Pagination cursor for next page")
    has_more: bool = Field(..., description="Whether there are more events available")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")

