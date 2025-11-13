"""Integration tests for full event flow."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, AsyncMock

from app.main import app
from app.core.auth import CUSTOMER_API_KEYS
from app.database.models import Subscription
from app.services.subscription_service import subscription_service

client = TestClient(app)


class TestEventFlow:
    """Integration tests for complete event flow."""

    @pytest.fixture
    def mock_subscription(self):
        """Create a mock subscription."""
        subscription = Mock(spec=Subscription)
        subscription.workflow_id = "test-workflow-id"
        subscription.customer_id = "customer-123"
        subscription.event_selector = {
            "type": "event_type",
            "value": "order.created",
        }
        subscription.webhook_url = "https://hooks.zapier.com/hooks/catch/test/123456"
        subscription.status = "active"
        return subscription

    @pytest.mark.asyncio
    async def test_full_event_flow(self, mock_subscription):
        """Test complete event flow from submission to delivery."""
        # Mock subscription service
        with patch.object(
            subscription_service,
            "get_subscriptions",
            return_value=[mock_subscription],
        ):
            # Submit event
            response = client.post(
                "/api/v1/events",
                json={
                    "payload": {
                        "event_type": "order.created",
                        "order_id": "12345",
                        "amount": 99.99,
                    }
                },
                headers={"Authorization": "Bearer test-api-key-123"},
            )

            assert response.status_code == 202
            data = response.json()
            assert "event_id" in data
            assert data["status"] == "accepted"

            event_id = data["event_id"]

            # Verify event can be retrieved
            response = client.get(
                "/api/v1/inbox",
                headers={"Authorization": "Bearer test-api-key-123"},
            )

            assert response.status_code == 200
            inbox_data = response.json()
            assert "events" in inbox_data

    @pytest.mark.asyncio
    async def test_event_matching(self, mock_subscription):
        """Test event matching against subscriptions."""
        from app.core.matching import EventMatcher

        # Test matching event
        event_payload = {
            "event_type": "order.created",
            "order_id": "12345",
            "amount": 99.99,
        }

        matching = EventMatcher.match_event_to_subscriptions(
            event_payload=event_payload,
            subscriptions=[mock_subscription],
        )

        assert len(matching) == 1
        assert matching[0].workflow_id == mock_subscription.workflow_id

        # Test non-matching event
        non_matching_payload = {
            "event_type": "order.cancelled",
            "order_id": "12345",
        }

        matching = EventMatcher.match_event_to_subscriptions(
            event_payload=non_matching_payload,
            subscriptions=[mock_subscription],
        )

        assert len(matching) == 0

    @pytest.mark.asyncio
    async def test_event_with_multiple_subscriptions(self):
        """Test event matching against multiple subscriptions."""
        from app.core.matching import EventMatcher

        # Create multiple subscriptions
        subscription1 = Mock(spec=Subscription)
        subscription1.workflow_id = "workflow-1"
        subscription1.event_selector = {"type": "event_type", "value": "order.created"}
        subscription1.webhook_url = "https://hooks.zapier.com/hooks/catch/test/1"

        subscription2 = Mock(spec=Subscription)
        subscription2.workflow_id = "workflow-2"
        subscription2.event_selector = {"type": "event_type", "value": "order.created"}
        subscription2.webhook_url = "https://hooks.zapier.com/hooks/catch/test/2"

        subscription3 = Mock(spec=Subscription)
        subscription3.workflow_id = "workflow-3"
        subscription3.event_selector = {"type": "event_type", "value": "order.cancelled"}
        subscription3.webhook_url = "https://hooks.zapier.com/hooks/catch/test/3"

        event_payload = {
            "event_type": "order.created",
            "order_id": "12345",
        }

        matching = EventMatcher.match_event_to_subscriptions(
            event_payload=event_payload,
            subscriptions=[subscription1, subscription2, subscription3],
        )

        # Should match first two subscriptions
        assert len(matching) == 2
        assert matching[0].workflow_id in ["workflow-1", "workflow-2"]
        assert matching[1].workflow_id in ["workflow-1", "workflow-2"]

    @pytest.mark.asyncio
    async def test_webhook_delivery(self, mock_subscription):
        """Test webhook delivery service."""
        from app.services.webhook_service import webhook_service
        from unittest.mock import AsyncMock

        # Mock HTTP client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={"success": True})

        with patch.object(webhook_service, "client") as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            events = [
                {
                    "event_id": "test-event-id",
                    "customer_id": "customer-123",
                    "payload": {"event_type": "order.created"},
                }
            ]

            success, error = await webhook_service.deliver_webhook(
                subscription=mock_subscription,
                events=events,
            )

            assert success is True
            assert error is None
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_webhook_delivery_with_retry(self, mock_subscription):
        """Test webhook delivery with retry logic."""
        from app.services.webhook_service import webhook_service

        # Mock HTTP client that fails first, then succeeds
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = Mock()
            if call_count == 1:
                mock_response.status_code = 500  # First call fails
            else:
                mock_response.status_code = 200  # Second call succeeds
            return mock_response

        with patch.object(webhook_service, "client") as mock_client:
            mock_client.post = AsyncMock(side_effect=mock_post)

            events = [
                {
                    "event_id": "test-event-id",
                    "customer_id": "customer-123",
                    "payload": {"event_type": "order.created"},
                }
            ]

            success, attempts, error = await webhook_service.deliver_with_retry(
                subscription=mock_subscription,
                events=events,
                max_retries=3,
            )

            # Should succeed after retry
            assert success is True
            assert attempts == 2  # First attempt + 1 retry
            assert error is None

