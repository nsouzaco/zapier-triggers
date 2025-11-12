"""Service for delivering webhooks to workflow execution engine."""

import asyncio
import time
from datetime import datetime
from typing import List, Optional

import httpx

from app.config import get_settings
from app.database.models import Subscription
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class WebhookService:
    """Service for delivering webhooks to Zapier workflow execution engine."""

    def __init__(self):
        """Initialize webhook service."""
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(
            timeout=settings.webhook_timeout_seconds,
            follow_redirects=True,
        )

    async def deliver_webhook(
        self,
        subscription: Subscription,
        events: List[dict],
    ) -> tuple[bool, Optional[str]]:
        """
        Deliver webhook to workflow execution engine.

        Args:
            subscription: Subscription with webhook URL
            events: List of events to deliver

        Returns:
            Tuple of (success, error_message)
        """
        if not self.client:
            return False, "Webhook client not initialized"

        try:
            # Prepare webhook payload
            # Zapier expects array-based webhook payloads
            payload = events if isinstance(events, list) else [events]

            # Send webhook
            response = await self.client.post(
                subscription.webhook_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Zapier-Triggers-API/1.0",
                },
            )

            # Handle response
            if response.status_code == 200 or response.status_code == 201:
                logger.info(
                    f"Webhook delivered successfully: {subscription.workflow_id} "
                    f"({len(events)} events)"
                )
                return True, None
            elif response.status_code == 410:
                # 410 Gone - subscription is no longer valid
                logger.warning(
                    f"Webhook returned 410 Gone: {subscription.workflow_id}. "
                    "Subscription should be deactivated."
                )
                return False, "Subscription no longer valid (410 Gone)"
            elif response.status_code >= 400 and response.status_code < 500:
                # Client error - don't retry
                logger.warning(
                    f"Webhook returned client error {response.status_code}: "
                    f"{subscription.workflow_id}"
                )
                return False, f"Client error: {response.status_code}"
            else:
                # Server error - retry
                logger.warning(
                    f"Webhook returned server error {response.status_code}: "
                    f"{subscription.workflow_id}"
                )
                return False, f"Server error: {response.status_code}"

        except httpx.TimeoutException:
            logger.warning(f"Webhook timeout: {subscription.workflow_id}")
            return False, "Timeout"
        except httpx.RequestError as e:
            logger.error(
                f"Webhook request error: {e} for {subscription.workflow_id}",
                exc_info=True
            )
            # Log the underlying exception details if available
            if hasattr(e, 'request'):
                logger.error(f"Request URL: {e.request.url if e.request else 'N/A'}")
            return False, f"Request error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error delivering webhook: {e}", exc_info=True)
            return False, f"Unexpected error: {str(e)}"

    async def deliver_with_retry(
        self,
        subscription: Subscription,
        events: List[dict],
        max_retries: Optional[int] = None,
    ) -> tuple[bool, int, Optional[str]]:
        """
        Deliver webhook with exponential backoff retry.

        Args:
            subscription: Subscription with webhook URL
            events: List of events to deliver
            max_retries: Maximum number of retry attempts (default from settings)

        Returns:
            Tuple of (success, attempts, error_message)
        """
        if max_retries is None:
            max_retries = settings.webhook_max_retries

        attempts = 0
        last_error = None

        while attempts < max_retries:
            attempts += 1
            success, error = await self.deliver_webhook(subscription, events)

            if success:
                return True, attempts, None

            last_error = error

            # Don't retry on client errors (4xx) except 429
            if error and "Client error:" in error:
                status_code = int(error.split(":")[1].strip())
                if status_code != 429:  # Rate limit - retry
                    break

            # Don't retry on 410 Gone
            if error and "410 Gone" in error:
                break

            # Calculate backoff delay
            if attempts < max_retries:
                delay = min(
                    settings.webhook_retry_backoff_base ** attempts,
                    settings.webhook_retry_max_delay_seconds,
                )
                logger.info(
                    f"Retrying webhook delivery in {delay}s "
                    f"(attempt {attempts}/{max_retries}): {subscription.workflow_id}"
                )
                await asyncio.sleep(delay)

        logger.error(
            f"Webhook delivery failed after {attempts} attempts: "
            f"{subscription.workflow_id} - {last_error}"
        )
        return False, attempts, last_error

    async def close(self):
        """Close HTTP client."""
        if self.client:
            await self.client.aclose()


# Global webhook service instance
webhook_service = WebhookService()

