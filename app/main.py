"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.utils.logging import setup_logging

settings = get_settings()

# Set up logging before creating the app
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup
    logger = app.state.logger
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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store logger in app state
import logging
app.state.logger = logging.getLogger(__name__)


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


# Import and include routers
# from app.api import events, inbox
# app.include_router(events.router, prefix="/api/v1", tags=["events"])
# app.include_router(inbox.router, prefix="/api/v1", tags=["inbox"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
    )

