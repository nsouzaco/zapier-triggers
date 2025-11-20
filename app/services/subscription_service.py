"""Service for managing workflow subscriptions."""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings
from app.database.models import Subscription, Base
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class SubscriptionService:
    """Service for managing workflow subscriptions."""

    def __init__(self):
        """Initialize subscription service."""
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database connection."""
        try:
            self.engine = create_engine(
                settings.postgresql_url,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_pre_ping=True,
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create tables if they don't exist
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("PostgreSQL database connection initialized")
        except Exception as e:
            logger.warning(f"PostgreSQL not available: {e}. Subscription service disabled.")
            self.engine = None
            self.SessionLocal = None

    def get_session(self) -> Optional[Session]:
        """Get database session."""
        if not self.SessionLocal:
            return None
        return self.SessionLocal()

    async def get_subscriptions(self, customer_id: str) -> List[Subscription]:
        """
        Get all active subscriptions for a customer.

        Args:
            customer_id: Customer identifier

        Returns:
            List of active subscriptions
        """
        if not self.SessionLocal:
            logger.debug("Database not available, returning empty subscriptions")
            return []

        session = self.get_session()
        if not session:
            return []

        try:
            stmt = select(Subscription).where(
                Subscription.customer_id == customer_id,
                Subscription.status == "active",
            )
            result = session.execute(stmt)
            subscriptions = result.scalars().all()
            return list(subscriptions)
        except Exception as e:
            logger.error(f"Error retrieving subscriptions: {e}")
            return []
        finally:
            session.close()

    async def get_subscription(self, workflow_id: UUID) -> Optional[Subscription]:
        """
        Get subscription by workflow ID.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Subscription if found, None otherwise
        """
        if not self.SessionLocal:
            return None

        session = self.get_session()
        if not session:
            return None

        try:
            stmt = select(Subscription).where(Subscription.workflow_id == workflow_id)
            result = session.execute(stmt)
            subscription = result.scalar_one_or_none()
            return subscription
        except Exception as e:
            logger.error(f"Error retrieving subscription: {e}")
            return None
        finally:
            session.close()

    async def create_subscription(
        self,
        customer_id: str,
        event_selector: dict,
        webhook_url: str,
    ) -> Optional[Subscription]:
        """
        Create a new subscription.

        Args:
            customer_id: Customer identifier
            event_selector: Event selector/filter (JSONPath or event_type)
            webhook_url: Webhook URL for event delivery

        Returns:
            Created subscription if successful, None otherwise
        """
        if not self.SessionLocal:
            return None

        session = self.get_session()
        if not session:
            return None

        try:
            subscription = Subscription(
                customer_id=customer_id,
                event_selector=event_selector,
                webhook_url=webhook_url,
                status="active",
            )
            session.add(subscription)
            session.commit()
            session.refresh(subscription)
            logger.info(f"Subscription created: {subscription.workflow_id} for customer {customer_id}")
            return subscription
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating subscription: {e}")
            return None
        finally:
            session.close()

    async def update_subscription(
        self,
        workflow_id: UUID,
        event_selector: Optional[dict] = None,
        webhook_url: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bool:
        """
        Update an existing subscription.

        Args:
            workflow_id: Workflow identifier
            event_selector: Optional new event selector
            webhook_url: Optional new webhook URL
            status: Optional new status

        Returns:
            True if successfully updated, False otherwise
        """
        if not self.SessionLocal:
            return False

        session = self.get_session()
        if not session:
            return False

        try:
            stmt = select(Subscription).where(Subscription.workflow_id == workflow_id)
            result = session.execute(stmt)
            subscription = result.scalar_one_or_none()

            if not subscription:
                return False

            if event_selector is not None:
                subscription.event_selector = event_selector
            if webhook_url is not None:
                subscription.webhook_url = webhook_url
            if status is not None:
                subscription.status = status

            session.commit()
            logger.info(f"Subscription updated: {workflow_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating subscription: {e}")
            return False
        finally:
            session.close()

    async def delete_subscription(self, workflow_id: UUID) -> bool:
        """
        Delete a subscription.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if successfully deleted, False otherwise
        """
        if not self.SessionLocal:
            return False

        session = self.get_session()
        if not session:
            return False

        try:
            stmt = select(Subscription).where(Subscription.workflow_id == workflow_id)
            result = session.execute(stmt)
            subscription = result.scalar_one_or_none()

            if not subscription:
                return False

            session.delete(subscription)
            session.commit()
            logger.info(f"Subscription deleted: {workflow_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting subscription: {e}")
            return False
        finally:
            session.close()

    async def get_all_subscriptions(self) -> List[Subscription]:
        """
        Get all subscriptions across all customers (for operator dashboard).

        Returns:
            List of all subscriptions
        """
        if not self.SessionLocal:
            return []

        session = self.get_session()
        if not session:
            return []

        try:
            stmt = select(Subscription)
            result = session.execute(stmt)
            subscriptions = result.scalars().all()
            return list(subscriptions)
        except Exception as e:
            logger.error(f"Error retrieving all subscriptions: {e}")
            return []
        finally:
            session.close()


# Global subscription service instance
subscription_service = SubscriptionService()

