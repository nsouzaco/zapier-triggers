"""Authentication middleware for API key validation."""

from typing import Optional

from fastapi import Header, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.services.customer_service import customer_service
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

security = HTTPBearer()


async def get_customer_id_from_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> str:
    """
    Extract and validate API key from Authorization header.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        Customer ID associated with the API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    api_key = credentials.credentials

    if not api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Please provide a valid API key in the Authorization header.",
        )

    # Lookup customer from database
    try:
        logger.debug(f"Attempting to authenticate API key: {api_key[:10]}...")
        customer = customer_service.get_customer_by_api_key(api_key)
        
        if not customer:
            logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
            # Log additional debug info
            logger.debug(f"CustomerService session available: {customer_service.get_session() is not None}")
            raise HTTPException(
                status_code=401,
                detail="Invalid API key. Please provide a valid API key.",
            )

        logger.info(f"Authenticated request for customer: {customer.customer_id}")
        return customer.customer_id
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during authentication.",
        )


async def get_customer_id_optional(
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[str]:
    """
    Extract customer ID from API key if present (for optional auth endpoints).

    Args:
        authorization: Authorization header value

    Returns:
        Customer ID if valid API key provided, None otherwise
    """
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    api_key = authorization.replace("Bearer ", "").strip()
    try:
        customer = customer_service.get_customer_by_api_key(api_key)
        return customer.customer_id if customer else None
    except Exception:
        return None

