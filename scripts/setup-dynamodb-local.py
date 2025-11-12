#!/usr/bin/env python3
"""Create DynamoDB table in DynamoDB Local."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

settings = get_settings()

# DynamoDB Local endpoint
DYNAMODB_LOCAL_ENDPOINT = "http://localhost:8001"  # Changed from 8000 to 8001

def create_table():
    """Create DynamoDB events table."""
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=DYNAMODB_LOCAL_ENDPOINT,
        region_name=settings.aws_region,
        aws_access_key_id="dummy",  # Required but not used by DynamoDB Local
        aws_secret_access_key="dummy",  # Required but not used by DynamoDB Local
    )

    table_name = settings.dynamodb_events_table

    try:
        # Check if table exists
        table = dynamodb.Table(table_name)
        table.load()
        print(f"✅ Table {table_name} already exists")
        return table
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            # Table doesn't exist, create it
            print(f"📝 Creating table {table_name}...")
            table = dynamodb.create_table(
                TableName=table_name,
                KeySchema=[
                    {
                        "AttributeName": "customer_id",
                        "KeyType": "HASH"  # Partition key
                    },
                    {
                        "AttributeName": "event_id",
                        "KeyType": "RANGE"  # Sort key
                    }
                ],
                AttributeDefinitions=[
                    {
                        "AttributeName": "customer_id",
                        "AttributeType": "S"
                    },
                    {
                        "AttributeName": "event_id",
                        "AttributeType": "S"
                    }
                ],
                BillingMode="PAY_PER_REQUEST"  # On-demand
            )

            # Wait for table to be created
            print("⏳ Waiting for table to be created...")
            table.wait_until_exists()
            print(f"✅ Table {table_name} created successfully")
            return table
        else:
            print(f"❌ Error: {e}")
            raise

if __name__ == "__main__":
    try:
        create_table()
        print("\n✅ DynamoDB Local setup complete!")
    except Exception as e:
        print(f"\n❌ Error setting up DynamoDB Local: {e}")
        exit(1)

