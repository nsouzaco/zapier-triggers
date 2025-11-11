"""AWS service clients and utilities."""

import os
import boto3
from botocore.config import Config
from typing import Optional

from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Check if running in local development mode
IS_LOCAL_DEV = os.getenv('IS_LOCAL_DEV', 'false').lower() == 'true'

# Lazy-initialized clients (initialized on first use, not at import time)
_sqs_client = None
_dynamodb_client = None
_dynamodb_resource = None
_session = None


def verify_credentials():
    """
    Verify IAM role credentials are working.
    
    This should be called at the start of Lambda handler to confirm credentials are valid.
    """
    try:
        sts = boto3.client('sts', region_name=settings.aws_region)
        identity = sts.get_caller_identity()
        logger.info(f"✓ Credentials valid. Role ARN: {identity['Arn']}")
        return True
    except Exception as e:
        logger.error(f"✗ Credential check failed: {e}")
        return False


def _get_boto3_session(force_refresh: bool = False):
    """
    Get or create a boto3 Session with credential refresh support.
    
    In Lambda VPC environments, credentials are obtained via STS VPC endpoint.
    This function ensures credentials are properly refreshed when needed.
    
    IMPORTANT: Do NOT pass explicit credentials to boto3 in Lambda.
    Let boto3 use the credential chain (IMDS -> IAM role) automatically.
    
    Args:
        force_refresh: If True, create a new session to force credential refresh
        
    Returns:
        boto3.Session instance
    """
    global _session
    
    if _session is None or force_refresh:
        try:
            # Create a fresh session WITHOUT explicit credentials
            # In Lambda VPC, boto3 will automatically:
            # 1. Check environment variables (none set in Lambda) ✓
            # 2. Check ~/.aws/credentials (doesn't exist in Lambda) ✓
            # 3. Use IMDS via STS VPC endpoint ✓ ← Uses IAM role
            _session = boto3.Session(region_name=settings.aws_region)
            
            # Verify credentials are available
            credentials = _session.get_credentials()
            if credentials is None:
                logger.warning("No credentials found in session. This may cause issues in Lambda VPC.")
            else:
                if hasattr(credentials, 'access_key') and credentials.access_key:
                    logger.debug("Session credentials obtained successfully")
                else:
                    logger.warning("Credentials found but appear invalid")
                
        except Exception as e:
            logger.error(f"Error creating boto3 session: {e}", exc_info=True)
            # Re-raise to allow caller to handle
            raise
    
    return _session


def get_boto3_config() -> Config:
    """Get boto3 configuration with retries and timeouts."""
    return Config(
        retries={
            "max_attempts": 3,
            "mode": "adaptive",
        },
        connect_timeout=5,
        read_timeout=10,
    )


def clear_aws_clients():
    """Clear all cached AWS clients to force re-initialization with fresh credentials."""
    global _sqs_client, _dynamodb_client, _dynamodb_resource, _session
    logger.info("Clearing cached AWS clients to force credential refresh")
    _sqs_client = None
    _dynamodb_client = None
    _dynamodb_resource = None
    _session = None


def get_sqs_client(force_refresh: bool = False):
    """
    Get SQS client (lazy-initialized).
    
    Args:
        force_refresh: If True, clear cached client and create new one with fresh credentials
        
    Returns:
        boto3 SQS client
    """
    global _sqs_client
    
    if _sqs_client is None or force_refresh:
        if force_refresh:
            _sqs_client = None
        
        # Create a fresh session to ensure credentials are loaded from IAM role
        # In Lambda VPC, this will use STS VPC endpoint via private DNS
        session = _get_boto3_session(force_refresh=force_refresh)
        
        client_kwargs = {
            "service_name": "sqs",
            "region_name": settings.aws_region,
            "config": get_boto3_config(),
        }
        
        # NEVER pass explicit credentials in Lambda VPC environment
        # Let boto3 use the IAM role via credential chain (IMDS -> STS VPC endpoint)
        # Only use explicit credentials in local development
        if IS_LOCAL_DEV:
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
                client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        
        try:
            _sqs_client = session.client(**client_kwargs)
            logger.debug("SQS client created successfully")
        except Exception as e:
            logger.error(f"Error creating SQS client: {e}", exc_info=True)
            raise
    
    return _sqs_client


def get_dynamodb_client(force_refresh: bool = False):
    """
    Get DynamoDB client (lazy-initialized).
    
    Args:
        force_refresh: If True, clear cached client and create new one with fresh credentials
        
    Returns:
        boto3 DynamoDB client
    """
    global _dynamodb_client
    
    if _dynamodb_client is None or force_refresh:
        if force_refresh:
            _dynamodb_client = None
        
        # Use DynamoDB Local endpoint if in development and no AWS credentials
        endpoint_url = None
        if settings.is_development and not settings.aws_access_key_id:
            endpoint_url = "http://localhost:8001"  # DynamoDB Local port
        
        # Create a fresh session to ensure credentials are loaded from IAM role
        # In Lambda VPC, this will use STS VPC endpoint via private DNS
        session = _get_boto3_session(force_refresh=force_refresh)
        
        client_kwargs = {
            "service_name": "dynamodb",
            "region_name": settings.aws_region,
            "config": get_boto3_config(),
        }
        
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        
        # NEVER pass explicit credentials in Lambda VPC environment
        # Let boto3 use the IAM role via credential chain
        # Only use explicit credentials in local development
        if IS_LOCAL_DEV:
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
                client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        elif endpoint_url:
            # For DynamoDB Local, use dummy credentials
            client_kwargs["aws_access_key_id"] = "dummy"
            client_kwargs["aws_secret_access_key"] = "dummy"
        
        try:
            _dynamodb_client = session.client(**client_kwargs)
            logger.debug("DynamoDB client created successfully")
        except Exception as e:
            logger.error(f"Error creating DynamoDB client: {e}", exc_info=True)
            raise
    
    return _dynamodb_client


def get_dynamodb_resource(force_refresh: bool = False):
    """
    Get DynamoDB resource (lazy-initialized).
    
    Args:
        force_refresh: If True, clear cached resource and create new one with fresh credentials
        
    Returns:
        boto3 DynamoDB resource
    """
    global _dynamodb_resource
    
    if _dynamodb_resource is None or force_refresh:
        if force_refresh:
            _dynamodb_resource = None
        
        # Create a fresh session to ensure credentials are loaded from IAM role
        # In Lambda VPC, this will use STS VPC endpoint via private DNS
        session = _get_boto3_session(force_refresh=force_refresh)
        
        # Use DynamoDB Local endpoint if in development and no AWS credentials
        endpoint_url = None
        if settings.is_development and not settings.aws_access_key_id:
            endpoint_url = "http://localhost:8001"  # DynamoDB Local port
        
        resource_kwargs = {
            "service_name": "dynamodb",
            "region_name": settings.aws_region,
            "config": get_boto3_config(),
        }
        
        if endpoint_url:
            resource_kwargs["endpoint_url"] = endpoint_url
        
        # NEVER pass explicit credentials in Lambda VPC environment
        # Let boto3 use the IAM role via credential chain
        # Only use explicit credentials in local development
        if IS_LOCAL_DEV:
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                resource_kwargs["aws_access_key_id"] = settings.aws_access_key_id
                resource_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        elif endpoint_url:
            # For DynamoDB Local, use dummy credentials
            resource_kwargs["aws_access_key_id"] = "dummy"
            resource_kwargs["aws_secret_access_key"] = "dummy"
        
        try:
            _dynamodb_resource = session.resource(**resource_kwargs)
            logger.debug("DynamoDB resource created successfully")
        except Exception as e:
            logger.error(f"Error creating DynamoDB resource: {e}", exc_info=True)
            raise
    
    return _dynamodb_resource

