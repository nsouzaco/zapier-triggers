"""AWS service clients and utilities."""

import boto3
from botocore.config import Config
from typing import Optional

from app.config import get_settings

settings = get_settings()


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


def get_sqs_client():
    """Get SQS client."""
    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=get_boto3_config(),
    )


def get_dynamodb_client():
    """Get DynamoDB client."""
    return boto3.client(
        "dynamodb",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=get_boto3_config(),
    )


def get_dynamodb_resource():
    """Get DynamoDB resource."""
    return boto3.resource(
        "dynamodb",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=get_boto3_config(),
    )

