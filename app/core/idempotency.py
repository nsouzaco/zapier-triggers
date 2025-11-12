"""Idempotency key handling."""

import json
from typing import Optional

from fastapi import Header

from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class IdempotencyHandler:
    """Handler for idempotency keys."""

    def __init__(self):
        """Initialize idempotency handler."""
        self.redis_client = None
        self._initialize_redis()

    def _initialize_redis(self):
        """Initialize Redis client."""
        try:
            import redis

            redis_host = settings.redis_endpoint or settings.redis_host
            self.redis_client = redis.Redis(
                host=redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            self.redis_client.ping()
            logger.info("Redis connection established for idempotency")
        except Exception as e:
            logger.warning(f"Redis not available for idempotency: {e}. Idempotency disabled.")
            self.redis_client = None

    async def get_cached_response(self, idempotency_key: str) -> Optional[dict]:
        """
        Get cached response for idempotency key.

        Args:
            idempotency_key: Idempotency key to lookup

        Returns:
            Cached response if found, None otherwise
        """
        if not self.redis_client:
            return None

        try:
            cached_data = self.redis_client.get(f"idempotency:{idempotency_key}")
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.error(f"Error getting cached idempotency response: {e}")
            return None

    async def cache_response(self, idempotency_key: str, event_id: str, response_data: dict):
        """
        Cache response for idempotency key.

        Args:
            idempotency_key: Idempotency key
            event_id: Event ID that was generated
            response_data: Response data to cache
        """
        if not self.redis_client:
            return

        try:
            cache_data = {
                "event_id": event_id,
                "response": response_data,
            }
            ttl_seconds = settings.idempotency_ttl_hours * 3600
            self.redis_client.setex(
                f"idempotency:{idempotency_key}",
                ttl_seconds,
                json.dumps(cache_data),
            )
            logger.debug(f"Cached idempotency response for key: {idempotency_key[:10]}...")
        except Exception as e:
            logger.error(f"Error caching idempotency response: {e}")


# Global idempotency handler instance
idempotency_handler = IdempotencyHandler()


async def get_idempotency_key(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
) -> Optional[str]:
    """
    Extract idempotency key from request header.

    Args:
        idempotency_key: Idempotency-Key header value

    Returns:
        Idempotency key if present, None otherwise
    """
    return idempotency_key

