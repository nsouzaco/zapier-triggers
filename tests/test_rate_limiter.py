"""Tests for rate limiting."""

import pytest
from unittest.mock import Mock, patch

from app.core.rate_limiter import RateLimiter, rate_limiter


class TestRateLimiter:
    """Tests for rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter()
        # Should initialize without errors (Redis may not be available)
        assert limiter is not None

    @pytest.mark.asyncio
    async def test_rate_limit_check_no_redis(self):
        """Test rate limit check when Redis is not available."""
        limiter = RateLimiter()
        limiter.redis_client = None  # Simulate no Redis
        
        is_allowed, retry_after = await limiter.check_rate_limit("test-key")
        # Should allow request when Redis is not available (fail open)
        assert is_allowed is True
        assert retry_after is None

    @pytest.mark.asyncio
    async def test_rate_limit_check_with_redis(self):
        """Test rate limit check with Redis available."""
        limiter = RateLimiter()
        
        # Mock Redis client
        mock_redis = Mock()
        mock_redis.get.return_value = "500"  # Current count
        mock_redis.incr.return_value = 501
        mock_redis.expire.return_value = True
        
        limiter.redis_client = mock_redis
        
        is_allowed, retry_after = await limiter.check_rate_limit("test-key")
        # Should allow if under limit
        assert is_allowed is True
        assert retry_after is None
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """Test rate limit when exceeded."""
        limiter = RateLimiter()
        
        # Mock Redis client with count at limit
        mock_redis = Mock()
        mock_redis.get.return_value = "1000"  # At limit
        
        limiter.redis_client = mock_redis
        
        is_allowed, retry_after = await limiter.check_rate_limit("test-key")
        # Should reject if at or over limit
        assert is_allowed is False
        assert retry_after is not None

    @pytest.mark.asyncio
    async def test_rate_limit_redis_error(self):
        """Test rate limit when Redis raises an error."""
        limiter = RateLimiter()
        
        # Mock Redis client that raises an error
        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Redis error")
        
        limiter.redis_client = mock_redis
        
        is_allowed, retry_after = await limiter.check_rate_limit("test-key")
        # Should fail open (allow request) on error
        assert is_allowed is True
        assert retry_after is None

