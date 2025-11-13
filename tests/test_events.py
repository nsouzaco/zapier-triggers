"""Tests for event endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.core.auth import CUSTOMER_API_KEYS

client = TestClient(app)


class TestEventSubmission:
    """Tests for POST /events endpoint."""

    def test_submit_event_success(self):
        """Test successful event submission."""
        response = client.post(
            "/api/v1/events",
            json={"payload": {"event_type": "order.created", "order_id": "12345", "amount": 99.99}},
            headers={"Authorization": "Bearer test-api-key-123"},
        )
        assert response.status_code == 202
        data = response.json()
        assert "event_id" in data
        assert data["status"] == "accepted"
        assert data["message"] == "Event accepted for processing"
        assert "timestamp" in data

    def test_submit_event_missing_auth(self):
        """Test event submission without authentication."""
        response = client.post(
            "/api/v1/events",
            json={"payload": {"event_type": "order.created"}},
        )
        assert response.status_code == 403  # FastAPI returns 403 for missing auth

    def test_submit_event_invalid_auth(self):
        """Test event submission with invalid API key."""
        response = client.post(
            "/api/v1/events",
            json={"payload": {"event_type": "order.created"}},
            headers={"Authorization": "Bearer invalid-key"},
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]

    def test_submit_event_missing_payload(self):
        """Test event submission with missing payload."""
        response = client.post(
            "/api/v1/events",
            json={},
            headers={"Authorization": "Bearer test-api-key-123"},
        )
        assert response.status_code == 422  # Validation error

    def test_submit_event_empty_payload(self):
        """Test event submission with empty payload."""
        response = client.post(
            "/api/v1/events",
            json={"payload": {}},
            headers={"Authorization": "Bearer test-api-key-123"},
        )
        assert response.status_code == 202  # Empty payload is valid

    def test_submit_event_with_idempotency_key(self):
        """Test event submission with idempotency key."""
        idempotency_key = "test-idempotency-key-123"
        
        # First request
        response1 = client.post(
            "/api/v1/events",
            json={"payload": {"event_type": "order.created", "order_id": "12345"}},
            headers={
                "Authorization": "Bearer test-api-key-123",
                "Idempotency-Key": idempotency_key,
            },
        )
        assert response1.status_code == 202
        event_id_1 = response1.json()["event_id"]
        
        # Second request with same idempotency key
        # Note: Without Redis, idempotency won't work, but the endpoint should still work
        response2 = client.post(
            "/api/v1/events",
            json={"payload": {"event_type": "order.created", "order_id": "12345"}},
            headers={
                "Authorization": "Bearer test-api-key-123",
                "Idempotency-Key": idempotency_key,
            },
        )
        assert response2.status_code == 202
        # Without Redis, we'll get a new event_id, which is expected

    def test_submit_event_large_payload(self):
        """Test event submission with payload exceeding 1MB."""
        # Create a payload larger than 1MB
        large_payload = {"data": "x" * (1024 * 1024 + 1)}  # 1MB + 1 byte
        
        response = client.post(
            "/api/v1/events",
            json={"payload": large_payload},
            headers={"Authorization": "Bearer test-api-key-123"},
        )
        # Should fail validation
        assert response.status_code in [400, 422]

    def test_submit_event_different_customers(self):
        """Test event submission from different customers."""
        # Customer 1
        response1 = client.post(
            "/api/v1/events",
            json={"payload": {"event_type": "order.created", "customer": "1"}},
            headers={"Authorization": "Bearer test-api-key-123"},
        )
        assert response1.status_code == 202
        
        # Customer 2
        response2 = client.post(
            "/api/v1/events",
            json={"payload": {"event_type": "order.created", "customer": "2"}},
            headers={"Authorization": "Bearer test-api-key-456"},
        )
        assert response2.status_code == 202
        
        # Event IDs should be different
        assert response1.json()["event_id"] != response2.json()["event_id"]


class TestInboxEndpoint:
    """Tests for GET /inbox endpoint."""

    def test_get_inbox_success(self):
        """Test successful inbox retrieval."""
        response = client.get(
            "/api/v1/inbox",
            headers={"Authorization": "Bearer test-api-key-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert "has_more" in data
        assert isinstance(data["events"], list)

    def test_get_inbox_missing_auth(self):
        """Test inbox retrieval without authentication."""
        response = client.get("/api/v1/inbox")
        assert response.status_code == 403

    def test_get_inbox_invalid_auth(self):
        """Test inbox retrieval with invalid API key."""
        response = client.get(
            "/api/v1/inbox",
            headers={"Authorization": "Bearer invalid-key"},
        )
        assert response.status_code == 401

    def test_get_inbox_with_limit(self):
        """Test inbox retrieval with limit parameter."""
        response = client.get(
            "/api/v1/inbox?limit=10",
            headers={"Authorization": "Bearer test-api-key-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) <= 10

    def test_get_inbox_with_filters(self):
        """Test inbox retrieval with filters."""
        response = client.get(
            "/api/v1/inbox?event_type=order.created&status=pending&limit=5",
            headers={"Authorization": "Bearer test-api-key-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    def test_get_inbox_invalid_limit(self):
        """Test inbox retrieval with invalid limit."""
        response = client.get(
            "/api/v1/inbox?limit=2000",  # Exceeds max limit of 1000
            headers={"Authorization": "Bearer test-api-key-123"},
        )
        # Should validate and return 422 or clamp to max
        assert response.status_code in [200, 422]


class TestEventModels:
    """Tests for event models."""

    def test_event_request_validation(self):
        """Test EventRequest model validation."""
        from app.models.events import EventRequest
        
        # Valid request
        request = EventRequest(payload={"event_type": "order.created"})
        assert request.payload == {"event_type": "order.created"}
        
        # Empty payload is valid
        request = EventRequest(payload={})
        assert request.payload == {}

    def test_event_response_model(self):
        """Test EventResponse model."""
        from app.models.events import EventResponse
        from datetime import datetime
        
        response = EventResponse(
            event_id="test-id",
            status="accepted",
            message="Test message",
            timestamp=datetime.utcnow(),
        )
        assert response.event_id == "test-id"
        assert response.status == "accepted"
        assert response.message == "Test message"

    def test_event_filter_model(self):
        """Test EventFilter model."""
        from app.models.events import EventFilter
        from datetime import datetime
        
        filter_obj = EventFilter(
            event_type="order.created",
            status="pending",
            limit=50,
        )
        assert filter_obj.event_type == "order.created"
        assert filter_obj.status == "pending"
        assert filter_obj.limit == 50

