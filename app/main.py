"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api import events, inbox
from app.config import get_settings
from app.core.rate_limiter import RateLimitMiddleware
from app.utils.logging import setup_logging

settings = get_settings()

# Set up logging before creating the app
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup - use module-level logger instead of app.state.logger
    logger.info("Starting Zapier Triggers API", extra={"version": settings.api_version})

    # Initialize services here (database connections, etc.)
    # Example:
    # app.state.redis_client = await create_redis_client()
    # app.state.db_session = await create_db_session()

    yield

    # Shutdown
    logger.info("Shutting down Zapier Triggers API")
    # Cleanup here
    # Example:
    # await app.state.redis_client.close()
    # await app.state.db_session.close()


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
    lifespan=lifespan,
)

# Store logger in app state (for backward compatibility if needed)
app.state.logger = logger

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "status": "operational",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "environment": settings.environment,
    }


# Dev-only admin endpoint for creating test customers
if settings.is_development:
    from app.services.customer_service import customer_service
    from app.services.subscription_service import subscription_service
    from pydantic import BaseModel
    from typing import Optional, Dict, Any
    
    class CreateTestCustomerRequest(BaseModel):
        name: str = "Test Customer"
        email: str = "test@example.com"
    
    class CreateTestSubscriptionRequest(BaseModel):
        customer_id: str
        event_selector: Dict[str, Any]  # e.g., {"type": "event_type", "value": "order.created"}
        webhook_url: str = "https://webhook.site/unique-url"  # Default test webhook
    
    @app.post("/admin/test-customer")
    async def create_test_customer(request: CreateTestCustomerRequest):
        """Create a test customer with API key (dev only)."""
        try:
            customer = customer_service.create_customer(
                name=request.name,
                email=request.email,
                rate_limit_per_second=1000,
            )
            if customer:
                return {
                    "customer_id": customer.customer_id,
                    "api_key": customer.api_key,
                    "name": customer.name,
                    "email": customer.email,
                    "status": customer.status,
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create customer"
                )
        except Exception as e:
            logger.error(f"Error creating test customer: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error creating customer: {str(e)}"
            )
    
    @app.post("/admin/test-subscription")
    async def create_test_subscription(request: CreateTestSubscriptionRequest):
        """Create a test subscription (dev only)."""
        try:
            subscription = await subscription_service.create_subscription(
                customer_id=request.customer_id,
                event_selector=request.event_selector,
                webhook_url=request.webhook_url,
            )
            if subscription:
                return {
                    "workflow_id": str(subscription.workflow_id),
                    "customer_id": subscription.customer_id,
                    "event_selector": subscription.event_selector,
                    "webhook_url": subscription.webhook_url,
                    "status": subscription.status,
                    "created_at": subscription.created_at.isoformat(),
                }
            else:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create subscription"
                )
        except Exception as e:
            logger.error(f"Error creating test subscription: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Error creating subscription: {str(e)}"
            )


# Include API routers
app.include_router(events.router, prefix="/api/v1")
app.include_router(inbox.router, prefix="/api/v1")

# Include operator endpoints (no auth required)
from app.api import operators
app.include_router(operators.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
    )

