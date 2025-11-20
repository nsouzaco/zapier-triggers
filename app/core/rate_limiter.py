"""Rate limiting implementation using Redis."""

import time
from typing import Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter using sliding window algorithm."""

    def __init__(self):
        """Initialize rate limiter."""
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
            logger.info("Redis connection established for rate limiting")
        except Exception as e:
            logger.warning(f"Redis not available for rate limiting: {e}. Rate limiting disabled.")
            self.redis_client = None

    async def check_rate_limit(self, api_key: str) -> tuple[bool, Optional[int]]:
        """
        Check if request is within rate limit.

        Args:
            api_key: API key to check rate limit for

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if not self.redis_client:
            # If Redis is not available, allow request (for development)
            return True, None

        try:
            # Sliding window rate limiting
            window_start = int(time.time() / settings.rate_limit_window_seconds)
            key = f"rate_limit:{api_key}:{window_start}"

            # Get current count
            current_count = self.redis_client.get(key)
            if current_count is None:
                current_count = 0
            else:
                current_count = int(current_count)

            # Check if limit exceeded
            if current_count >= settings.rate_limit_per_second:
                retry_after = settings.rate_limit_window_seconds - (int(time.time()) % settings.rate_limit_window_seconds)
                logger.warning(f"Rate limit exceeded for API key: {api_key[:10]}...")
                return False, retry_after

            # Increment counter
            self.redis_client.incr(key)
            self.redis_client.expire(key, settings.rate_limit_window_seconds)

            return True, None

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            # On error, allow request (fail open)
            return True, None


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting."""

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health check, docs, and operator endpoints
        skip_paths = ["/health", "/docs", "/openapi.json", "/"]
        if request.url.path in skip_paths or request.url.path.startswith("/admin/operators"):
            return await call_next(request)

        # Get API key from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            # No auth header, skip rate limiting (will be caught by auth middleware)
            return await call_next(request)

        api_key = auth_header.replace("Bearer ", "").strip()

        # Check rate limit
        is_allowed, retry_after = await rate_limiter.check_rate_limit(api_key)

        if not is_allowed:
            response = Response(
                content='{"error": "rate_limit_exceeded", "message": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )
            if retry_after:
                response.headers["Retry-After"] = str(retry_after)
            return response

        return await call_next(request)

