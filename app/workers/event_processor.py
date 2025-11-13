"""Event processing worker for consuming events from queue."""

import json
from datetime import datetime
from typing import Dict, Any

from app.config import get_settings
from app.core.matching import EventMatcher
from app.services.email_service import email_service
from app.services.event_storage import event_storage
from app.services.subscription_service import subscription_service
from app.services.webhook_service import webhook_service
from app.utils.aws import get_sqs_client
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class EventProcessor:
    """Worker for processing events from SQS queue."""

    def __init__(self):
        """Initialize event processor."""
        self.sqs_client = None
        self._initialize_sqs()

    def _initialize_sqs(self):
        """Initialize SQS client."""
        try:
            self.sqs_client = get_sqs_client()
            logger.info("SQS client initialized for event processor")
        except Exception as e:
            logger.warning(f"SQS not available: {e}. Event processor disabled.")
            self.sqs_client = None

    async def process_event(
        self,
        customer_id: str,
        event_id: str,
        payload: Dict[str, Any],
        timestamp: str = None,
    ) -> bool:
        """
        Process an event with extracted fields.

        This method receives already-parsed fields instead of the raw message.

        Args:
            customer_id: Customer identifier
            event_id: Event identifier
            payload: Event payload dictionary
            timestamp: Optional timestamp string

        Returns:
            True if successfully processed, False otherwise
        """
        try:
            logger.info(f"Starting event processing: customer_id={customer_id}, event_id={event_id}")

            # Check if this is an urgent Jira ticket event and send email FIRST
            # (before subscription matching, so email is sent even if no subscriptions match)
            event_type = payload.get("event_type", "")
            if event_type == "jira.ticket.urgent":
                jira_ticket_text = payload.get("jira_ticket_text", "")
                urgency_reason = payload.get("urgency_reason", "Urgent Jira ticket detected")
                
                if jira_ticket_text:
                    logger.info(f"Sending urgent Jira ticket email for event {event_id}")
                    email_sent = await email_service.send_urgent_jira_notification(
                        jira_ticket_text=jira_ticket_text,
                        urgency_reason=urgency_reason,
                        event_id=event_id,
                    )
                    if email_sent:
                        logger.info(f"Urgent Jira ticket email sent successfully for event {event_id}")
                    else:
                        logger.warning(f"Failed to send urgent Jira ticket email for event {event_id}")

            # Get subscriptions for customer
            logger.info(f"Fetching subscriptions for customer: {customer_id}")
            try:
                subscriptions = await subscription_service.get_subscriptions(customer_id)
                logger.info(f"Found {len(subscriptions)} subscriptions for customer {customer_id}")
            except Exception as e:
                logger.error(f"Error fetching subscriptions: {e}", exc_info=True)
                # If we can't get subscriptions, mark as unmatched and continue
                logger.warning(f"Marking event {event_id} as unmatched due to subscription fetch error")
                await event_storage.update_event_status(
                    customer_id=customer_id,
                    event_id=event_id,
                    status="unmatched",
                )
                return True

            if not subscriptions:
                logger.info(f"No subscriptions found for customer {customer_id}")
                # Update event status to unmatched
                await event_storage.update_event_status(
                    customer_id=customer_id,
                    event_id=event_id,
                    status="unmatched",
                )
                return True

            # Match event against subscriptions
            matching_subscriptions = EventMatcher.match_event_to_subscriptions(
                event_payload=payload,
                subscriptions=subscriptions,
            )

            if not matching_subscriptions:
                logger.info(f"No matching subscriptions for event {event_id}")
                # Update event status to unmatched
                await event_storage.update_event_status(
                    customer_id=customer_id,
                    event_id=event_id,
                    status="unmatched",
                )
                return True

            # Deliver webhook to each matching subscription
            event_data = {
                "event_id": event_id,
                "customer_id": customer_id,
                "payload": payload,
                "timestamp": timestamp or datetime.utcnow().isoformat(),
            }

            delivery_success = False
            delivery_attempts = 0
            last_error = None

            for subscription in matching_subscriptions:
                delivery_attempts += 1
                success, attempts, error = await webhook_service.deliver_with_retry(
                    subscription=subscription,
                    events=[event_data],
                )

                if success:
                    delivery_success = True
                    # Update event status to delivered
                    await event_storage.update_event_status(
                        customer_id=customer_id,
                        event_id=event_id,
                        status="delivered",
                        delivery_attempts=delivery_attempts,
                        last_delivery_timestamp=datetime.utcnow(),
                    )
                    logger.info(
                        f"Event delivered successfully: {event_id} to "
                        f"workflow {subscription.workflow_id}"
                    )
                else:
                    last_error = error
                    # Update event status to failed
                    await event_storage.update_event_status(
                        customer_id=customer_id,
                        event_id=event_id,
                        status="failed",
                        delivery_attempts=delivery_attempts,
                        last_delivery_timestamp=datetime.utcnow(),
                    )
                    logger.error(
                        f"Event delivery failed: {event_id} to "
                        f"workflow {subscription.workflow_id} - {error}"
                    )

            return delivery_success

        except Exception as e:
            logger.error(f"Error processing event: {e}", exc_info=True)
            return False

    async def process_message(self, sqs_record: Dict[str, Any]) -> bool:
        """
        Process an SQS message from EventSourceMapping.

        EventSourceMapping provides:
        {
            "messageId": "abc123",
            "body": "{\"customer_id\":\"...\",\"event_id\":\"...\",\"payload\":{...}}",
            "attributes": {...},
            "messageAttributes": {...}
        }

        Args:
            sqs_record: SQS record from EventSourceMapping

        Returns:
            True if successfully processed, False otherwise
        """
        try:
            message_id = sqs_record.get("messageId", "unknown")
            logger.info(f"Processing SQS message: {message_id}")
            logger.debug(f"Record keys: {list(sqs_record.keys())}")

            # Extract the message body (lowercase "body" from SQS EventSourceMapping)
            # SQS provides the body as a JSON string
            body_str = sqs_record.get("body")

            if not body_str:
                logger.error(f"Missing body in SQS record {message_id}")
                return False

            # Parse the JSON body
            try:
                if isinstance(body_str, str):
                    body = json.loads(body_str)
                else:
                    body = body_str
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse body as JSON: {e}. Body: {body_str[:200]}")
                return False

            logger.debug(f"Parsed body keys: {list(body.keys())}")

            # Extract fields
            customer_id = body.get("customer_id")
            event_id = body.get("event_id")
            payload = body.get("payload")
            timestamp = body.get("timestamp")

            # Validate required fields
            if not customer_id:
                logger.error(f"Missing customer_id in message {message_id}")
                return False
            if not event_id:
                logger.error(f"Missing event_id in message {message_id}")
                return False
            if payload is None:
                logger.error(f"Missing payload in message {message_id}")
                return False

            logger.info(
                f"Valid message parsed. customer_id={customer_id}, "
                f"event_id={event_id}, timestamp={timestamp}"
            )

            # Parse payload if it's a string
            if isinstance(payload, str):
                payload = json.loads(payload)

            # Process the event with extracted fields
            success = await self.process_event(
                customer_id=customer_id,
                event_id=event_id,
                payload=payload,
                timestamp=timestamp,
            )

            return success

        except Exception as e:
            logger.error(f"Error processing SQS message: {e}", exc_info=True)
            return False


# Global event processor instance
event_processor = EventProcessor()

