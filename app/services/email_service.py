"""Email service for sending notifications via Resend."""

from typing import Optional

from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

try:
    from resend import Resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    logger.warning("Resend package not available. Email service disabled.")


class EmailService:
    """Service for sending emails via Resend."""

    def __init__(self):
        """Initialize email service."""
        self.resend_client = None
        self._initialize_resend()

    def _initialize_resend(self):
        """Initialize Resend client."""
        if not RESEND_AVAILABLE:
            logger.warning("Resend package not installed. Email service disabled.")
            return

        if not settings.resend_api_key:
            logger.warning("RESEND_API_KEY not configured. Email service disabled.")
            return

        try:
            self.resend_client = Resend(api_key=settings.resend_api_key)
            logger.info("Resend client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Resend client: {e}")
            self.resend_client = None

    async def send_urgent_jira_notification(
        self,
        jira_ticket_text: str,
        urgency_reason: str,
        event_id: Optional[str] = None,
    ) -> bool:
        """
        Send email notification for urgent Jira ticket.

        Args:
            jira_ticket_text: Full text of the Jira ticket
            urgency_reason: Reason why the ticket is considered urgent
            event_id: Optional event ID for tracking

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.resend_client:
            logger.warning("Resend client not available. Cannot send email.")
            return False

        try:
            # Format email content
            # Summary at the beginning, then full ticket text
            email_body = f"""URGENT JIRA TICKET DETECTED

Summary:
{urgency_reason}

{'Event ID: ' + event_id if event_id else ''}

---
Full Jira Ticket Text:
---
{jira_ticket_text}
"""

            # Send email via Resend
            params = {
                "from": "Zapier Triggers API <onboarding@resend.dev>",  # Default Resend sender
                "to": [settings.urgent_jira_email_recipient],
                "subject": "Urgent Jira Ticket Detected",
                "text": email_body,
            }

            result = self.resend_client.emails.send(params)

            # Resend SDK returns a dictionary with 'id' key on success
            if result and isinstance(result, dict) and result.get("id"):
                logger.info(
                    f"Urgent Jira ticket email sent successfully. "
                    f"Resend ID: {result.get('id')}, Event ID: {event_id}"
                )
                return True
            elif result and hasattr(result, "id"):
                # Handle object response format
                logger.info(
                    f"Urgent Jira ticket email sent successfully. "
                    f"Resend ID: {result.id}, Event ID: {event_id}"
                )
                return True
            else:
                logger.error(f"Failed to send email. Response: {result}")
                return False

        except Exception as e:
            logger.error(f"Error sending urgent Jira ticket email: {e}", exc_info=True)
            return False


# Global email service instance
email_service = EmailService()

