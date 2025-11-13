"""Tests for authentication."""

import pytest
from fastapi import HTTPException

from app.core.auth import get_customer_id_from_api_key, CUSTOMER_API_KEYS
from fastapi.security import HTTPAuthorizationCredentials


class TestAuthentication:
    """Tests for authentication middleware."""

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        """Test authentication with valid API key."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test-api-key-123",
        )
        customer_id = await get_customer_id_from_api_key(credentials)
        assert customer_id == "customer-123"

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        """Test authentication with invalid API key."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid-key",
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_customer_id_from_api_key(credentials)
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test authentication with missing API key."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="",
        )
        with pytest.raises(HTTPException) as exc_info:
            await get_customer_id_from_api_key(credentials)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_different_api_keys(self):
        """Test authentication with different API keys."""
        # Test key 1
        credentials1 = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test-api-key-123",
        )
        customer_id_1 = await get_customer_id_from_api_key(credentials1)
        assert customer_id_1 == "customer-123"
        
        # Test key 2
        credentials2 = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test-api-key-456",
        )
        customer_id_2 = await get_customer_id_from_api_key(credentials2)
        assert customer_id_2 == "customer-456"
        
        # Different keys should map to different customers
        assert customer_id_1 != customer_id_2

