"""Service for enqueueing events to SQS."""

import json
from typing import Optional
from uuid import uuid4

from app.config import get_settings
from app.utils.aws import get_sqs_client
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class QueueService:
    """Service for managing SQS queue operations."""

    def __init__(self):
        """Initialize queue service (lazy initialization)."""
        # Don't initialize SQS client at import time
        # It will be initialized on first use via the client property
        pass

    @property
    def sqs_client(self):
        """Get SQS client (lazy-initialized on first use)."""
        try:
            # Only force refresh if we've explicitly marked it as needing refresh
            # (e.g., after a credential error)
            force_refresh = hasattr(self, '_needs_refresh') and getattr(self, '_needs_refresh', False)
            if force_refresh:
                self._needs_refresh = False  # Reset flag after using it
            client = get_sqs_client(force_refresh=force_refresh)
            # Test connection on first access
            if not hasattr(self, '_sqs_initialized'):
                logger.info("SQS client initialized")
                self._sqs_initialized = True
            return client
        except Exception as e:
            logger.warning(f"SQS not available: {e}. Queue operations will fail.")
            return None

    async def enqueue_event(
        self,
        customer_id: str,
        event_id: str,
        payload: dict,
    ) -> bool:
        """
        Enqueue event to SQS queue with retry logic for credential issues.

        Args:
            customer_id: Customer identifier
            event_id: Unique event identifier
            payload: Event payload

        Returns:
            True if successfully enqueued, False otherwise
        """
        if not settings.sqs_event_queue_url:
            logger.debug("SQS queue URL not configured, using local mode")
            return False

        from botocore.exceptions import ClientError
        from time import sleep
        
        message_body = {
            "customer_id": customer_id,
            "event_id": event_id,
            "payload": payload,
            "timestamp": str(payload.get("timestamp", "")),
        }
        
        message_attributes = {
            "customer_id": {
                "StringValue": customer_id,
                "DataType": "String",
            },
            "event_id": {
                "StringValue": event_id,
                "DataType": "String",
            },
        }
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                client = self.sqs_client
                if not client:
                    logger.debug("SQS client not available, using local mode")
                    return False
                
                response = client.send_message(
                    QueueUrl=settings.sqs_event_queue_url,
                    MessageBody=json.dumps(message_body),
                    MessageAttributes=message_attributes,
                )
                
                logger.info(f"Event enqueued successfully: {event_id}")
                return True
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code in ['InvalidClientTokenId', 'UnrecognizedClientException']:
                    if attempt < max_retries - 1:
                        wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Credential error (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {wait_time}s with credential refresh..."
                        )
                        sleep(wait_time)
                        # Clear all cached clients and force credential refresh
                        from app.utils.aws import clear_aws_clients
                        clear_aws_clients()
                        # Mark that we need to force refresh on next client access
                        self._needs_refresh = True
                        continue
                logger.error(f"Error enqueueing event to SQS: {e}")
                return False
            except Exception as e:
                logger.error(f"Error enqueueing event to SQS: {e}")
                return False
        
        return False

    async def enqueue_event_local(self, customer_id: str, event_id: str, payload: dict) -> bool:
        """
        Enqueue event locally (for development without SQS).

        Args:
            customer_id: Customer identifier
            event_id: Unique event identifier
            payload: Event payload

        Returns:
            True (always succeeds in local mode)
        """
        logger.info(f"Event enqueued locally (development mode): {event_id} for customer {customer_id}")
        # In local development, we just log the event
        # In production, this would enqueue to SQS
        return True


# Global queue service instance
queue_service = QueueService()

