"""Tests for idempotency handling."""

import pytest
import json
from unittest.mock import Mock, patch

from app.core.idempotency import IdempotencyHandler, idempotency_handler


class TestIdempotencyHandler:
    """Tests for idempotency functionality."""

    @pytest.mark.asyncio
    async def test_idempotency_handler_initialization(self):
        """Test idempotency handler initialization."""
        handler = IdempotencyHandler()
        # Should initialize without errors (Redis may not be available)
        assert handler is not None

    @pytest.mark.asyncio
    async def test_get_cached_response_no_redis(self):
        """Test getting cached response when Redis is not available."""
        handler = IdempotencyHandler()
        handler.redis_client = None  # Simulate no Redis
        
        result = await handler.get_cached_response("test-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_response_not_found(self):
        """Test getting cached response when key not found."""
        handler = IdempotencyHandler()
        
        # Mock Redis client
        mock_redis = Mock()
        mock_redis.get.return_value = None
        
        handler.redis_client = mock_redis
        
        result = await handler.get_cached_response("test-key")
        assert result is None
        mock_redis.get.assert_called_once_with("idempotency:test-key")

    @pytest.mark.asyncio
    async def test_get_cached_response_found(self):
        """Test getting cached response when key exists."""
        handler = IdempotencyHandler()
        
        # Mock Redis client with cached data
        cached_data = {
            "event_id": "test-event-id",
            "response": {
                "event_id": "test-event-id",
                "status": "accepted",
                "message": "Event accepted for processing",
            },
        }
        mock_redis = Mock()
        mock_redis.get.return_value = json.dumps(cached_data)
        
        handler.redis_client = mock_redis
        
        result = await handler.get_cached_response("test-key")
        assert result is not None
        assert result["event_id"] == "test-event-id"
        assert "response" in result

    @pytest.mark.asyncio
    async def test_cache_response_no_redis(self):
        """Test caching response when Redis is not available."""
        handler = IdempotencyHandler()
        handler.redis_client = None  # Simulate no Redis
        
        # Should not raise an error
        await handler.cache_response(
            idempotency_key="test-key",
            event_id="test-event-id",
            response_data={"status": "accepted"},
        )

    @pytest.mark.asyncio
    async def test_cache_response_with_redis(self):
        """Test caching response with Redis available."""
        handler = IdempotencyHandler()
        
        # Mock Redis client
        mock_redis = Mock()
        mock_redis.setex.return_value = True
        
        handler.redis_client = mock_redis
        
        response_data = {
            "event_id": "test-event-id",
            "status": "accepted",
            "message": "Event accepted for processing",
        }
        
        await handler.cache_response(
            idempotency_key="test-key",
            event_id="test-event-id",
            response_data=response_data,
        )
        
        # Verify Redis was called
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "idempotency:test-key"
        assert call_args[0][1] == 86400  # 24 hours in seconds

    @pytest.mark.asyncio
    async def test_idempotency_redis_error(self):
        """Test idempotency when Redis raises an error."""
        handler = IdempotencyHandler()
        
        # Mock Redis client that raises an error
        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Redis error")
        
        handler.redis_client = mock_redis
        
        # Should return None on error (fail gracefully)
        result = await handler.get_cached_response("test-key")
        assert result is None

