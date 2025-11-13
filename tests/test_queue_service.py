"""Tests for queue service."""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from app.services.queue_service import QueueService, queue_service


class TestQueueService:
    """Tests for queue service functionality."""

    @pytest.mark.asyncio
    async def test_queue_service_initialization(self):
        """Test queue service initialization."""
        service = QueueService()
        # Should initialize without errors (SQS may not be available)
        assert service is not None

    @pytest.mark.asyncio
    async def test_enqueue_event_no_sqs(self):
        """Test enqueueing event when SQS is not available."""
        service = QueueService()
        service.sqs_client = None  # Simulate no SQS
        
        result = await service.enqueue_event(
            customer_id="customer-123",
            event_id="event-123",
            payload={"event_type": "order.created"},
        )
        # Should return False when SQS is not available
        assert result is False

    @pytest.mark.asyncio
    async def test_enqueue_event_local(self):
        """Test enqueueing event in local mode."""
        service = QueueService()
        
        result = await service.enqueue_event_local(
            customer_id="customer-123",
            event_id="event-123",
            payload={"event_type": "order.created"},
        )
        # Should always return True in local mode
        assert result is True

    @pytest.mark.asyncio
    async def test_enqueue_event_with_sqs(self):
        """Test enqueueing event with SQS available."""
        service = QueueService()
        
        # Mock SQS client
        mock_sqs = Mock()
        mock_sqs.send_message.return_value = {
            "MessageId": "test-message-id",
            "MD5OfBody": "test-md5",
        }
        
        service.sqs_client = mock_sqs
        
        # Mock settings
        with patch("app.services.queue_service.settings") as mock_settings:
            mock_settings.sqs_event_queue_url = "https://sqs.us-east-1.amazonaws.com/123456789/test-queue"
            
            result = await service.enqueue_event(
                customer_id="customer-123",
                event_id="event-123",
                payload={"event_type": "order.created", "order_id": "12345"},
            )
            
            assert result is True
            mock_sqs.send_message.assert_called_once()
            call_args = mock_sqs.send_message.call_args
            assert call_args[1]["QueueUrl"] == mock_settings.sqs_event_queue_url
            message_body = json.loads(call_args[1]["MessageBody"])
            assert message_body["customer_id"] == "customer-123"
            assert message_body["event_id"] == "event-123"
            assert message_body["payload"]["event_type"] == "order.created"

    @pytest.mark.asyncio
    async def test_enqueue_event_sqs_error(self):
        """Test enqueueing event when SQS raises an error."""
        service = QueueService()
        
        # Mock SQS client that raises an error
        mock_sqs = Mock()
        mock_sqs.send_message.side_effect = Exception("SQS error")
        
        service.sqs_client = mock_sqs
        
        # Mock settings
        with patch("app.services.queue_service.settings") as mock_settings:
            mock_settings.sqs_event_queue_url = "https://sqs.us-east-1.amazonaws.com/123456789/test-queue"
            
            result = await service.enqueue_event(
                customer_id="customer-123",
                event_id="event-123",
                payload={"event_type": "order.created"},
            )
            
            # Should return False on error
            assert result is False

