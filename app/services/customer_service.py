"""Service for managing customers and API keys."""

from typing import Optional
from uuid import uuid4
import secrets
import string

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings
from app.database.models import Customer, Base
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class CustomerService:
    """Service for customer and API key management."""

    def __init__(self):
        """Initialize the customer service with database connection."""
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database connection lazily."""
        try:
            db_url = settings.postgresql_url
            # Mask password in URL for logging
            safe_url = db_url.split('@')[1] if '@' in db_url else db_url
            logger.info(f"Initializing PostgreSQL connection to: {safe_url}")
            self.engine = create_engine(
                db_url,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_pre_ping=True,
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Test connection
            with self.engine.connect() as conn:
                logger.info("PostgreSQL connection test successful")
            
            # Create tables if they don't exist (only if connection succeeds)
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("PostgreSQL database connection initialized for CustomerService")
        except Exception as e:
            logger.error(f"PostgreSQL not available for CustomerService: {e}. Customer service disabled.", exc_info=True)
            self.engine = None
            self.SessionLocal = None

    def get_session(self) -> Optional[Session]:
        """Get a database session."""
        if not self.SessionLocal:
            # Try to initialize if not already done
            if not self.engine:
                self._initialize_database()
            if not self.SessionLocal:
                return None
        return self.SessionLocal()

    def get_customer_by_api_key(self, api_key: str) -> Optional[Customer]:
        """
        Get customer by API key.

        Args:
            api_key: API key to lookup

        Returns:
            Customer object if found, None otherwise
        """
        logger.info(f"Looking up customer by API key: {api_key[:10]}...")
        session = self.get_session()
        if not session:
            logger.error("CustomerService is not initialized. Cannot retrieve customer by API key.")
            logger.error(f"Engine status: {self.engine is not None}, SessionLocal status: {self.SessionLocal is not None}")
            return None
        try:
            logger.info(f"Querying database for API key: {api_key[:10]}...")
            # Log database connection info (masked)
            db_url = settings.postgresql_url
            safe_url = db_url.split('@')[1] if '@' in db_url else db_url
            logger.info(f"Database URL: postgresql://***@{safe_url}")
            
            # First, check total customers
            total_customers = session.query(Customer).count()
            logger.info(f"Total customers in database: {total_customers}")
            
            # Try query without status filter
            customer_no_status = session.query(Customer).filter(
                Customer.api_key == api_key
            ).first()
            if customer_no_status:
                logger.warning(f"Found customer without status filter: {customer_no_status.customer_id}, status: {customer_no_status.status}")
            
            # Query with status filter
            customer = session.query(Customer).filter(
                Customer.api_key == api_key,
                Customer.status == "active"
            ).first()
            if customer:
                logger.info(f"Found customer: {customer.customer_id} for API key: {api_key[:10]}...")
            else:
                logger.warning(f"No customer found for API key: {api_key[:10]}...")
                # List first few API keys for debugging
                sample_customers = session.query(Customer).limit(3).all()
                logger.info(f"Sample API keys in DB: {[c.api_key[:10] + '...' for c in sample_customers]}")
                # Also log full keys for debugging (in production, remove this)
                if sample_customers:
                    logger.info(f"Full sample API keys: {[c.api_key for c in sample_customers]}")
                    logger.info(f"Sample customer IDs: {[c.customer_id for c in sample_customers]}")
                # Check schema
                from sqlalchemy import inspect
                inspector = inspect(self.engine)
                schemas = inspector.get_schema_names()
                logger.info(f"Available schemas: {schemas}")
                tables = inspector.get_table_names(schema='public')
                logger.info(f"Tables in public schema: {tables}")
            return customer
        except Exception as e:
            logger.error(f"Error looking up customer by API key: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_customer_by_id(self, customer_id: str) -> Optional[Customer]:
        """
        Get customer by customer ID.

        Args:
            customer_id: Customer ID to lookup

        Returns:
            Customer object if found, None otherwise
        """
        session = self.get_session()
        if not session:
            logger.error("CustomerService is not initialized. Cannot retrieve customer by ID.")
            return None
        try:
            customer = session.query(Customer).filter(
                Customer.customer_id == customer_id
            ).first()
            return customer
        except Exception as e:
            logger.error(f"Error looking up customer by ID: {e}")
            return None
        finally:
            session.close()

    def create_customer(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        api_key: Optional[str] = None,
        rate_limit_per_second: int = 1000,
    ) -> Optional[Customer]:
        """
        Create a new customer with an API key.

        Args:
            name: Customer name
            email: Customer email
            api_key: Optional API key (generated if not provided)
            rate_limit_per_second: Rate limit per second

        Returns:
            Created Customer object if successful, None otherwise
        """
        session = self.get_session()
        if not session:
            logger.error("CustomerService is not initialized. Cannot create customer.")
            return None
        try:
            # Generate API key if not provided
            if not api_key:
                api_key = self.generate_api_key()

            # Generate customer ID
            customer_id = str(uuid4())

            customer = Customer(
                customer_id=customer_id,
                api_key=api_key,
                name=name,
                email=email,
                status="active",
                rate_limit_per_second=rate_limit_per_second,
            )

            session.add(customer)
            session.commit()
            session.refresh(customer)

            logger.info(f"Created customer: {customer_id} with API key")
            return customer
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating customer: {e}")
            raise
        finally:
            session.close()

    def generate_api_key(self, length: int = 32) -> str:
        """
        Generate a secure random API key.

        Args:
            length: Length of the API key

        Returns:
            Generated API key string
        """
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    def list_customers(self) -> list[Customer]:
        """
        List all customers.

        Returns:
            List of Customer objects
        """
        session = self.get_session()
        if not session:
            logger.error("CustomerService is not initialized. Cannot list customers.")
            return []
        try:
            customers = session.query(Customer).all()
            return customers
        except Exception as e:
            logger.error(f"Error listing customers: {e}")
            return []
        finally:
            session.close()

    def update_customer_status(self, customer_id: str, status: str) -> bool:
        """
        Update customer status.

        Args:
            customer_id: Customer ID
            status: New status (active, disabled)

        Returns:
            True if successful, False otherwise
        """
        session = self.get_session()
        if not session:
            logger.error("CustomerService is not initialized. Cannot update customer status.")
            return False
        try:
            customer = session.query(Customer).filter(
                Customer.customer_id == customer_id
            ).first()

            if not customer:
                return False

            customer.status = status
            session.commit()
            logger.info(f"Updated customer {customer_id} status to {status}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating customer status: {e}")
            return False
        finally:
            session.close()

    def delete_customer(self, customer_id: str) -> bool:
        """
        Delete a customer.

        Args:
            customer_id: Customer ID to delete

        Returns:
            True if successful, False otherwise
        """
        session = self.get_session()
        if not session:
            logger.error("CustomerService is not initialized. Cannot delete customer.")
            return False
        try:
            customer = session.query(Customer).filter(
                Customer.customer_id == customer_id
            ).first()

            if not customer:
                return False

            session.delete(customer)
            session.commit()
            logger.info(f"Deleted customer: {customer_id}")
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting customer: {e}")
            return False
        finally:
            session.close()


# Global instance
customer_service = CustomerService()

