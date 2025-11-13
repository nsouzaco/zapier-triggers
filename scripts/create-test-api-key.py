#!/usr/bin/env python3
"""One-time script to create a test API key via Lambda invocation."""

import json
import boto3
import sys

def create_test_api_key():
    """Invoke Lambda function to create a test API key."""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Create a simple Lambda function payload that will create a test customer
    payload = {
        "path": "/admin/test-customer",
        "httpMethod": "POST",
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "name": "Test Customer",
            "email": "test@example.com"
        })
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='zapier-triggers-api-dev-api',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result.get('body', '{}'))
            print(f"\n✅ Test API key created!")
            print(f"Customer ID: {body.get('customer_id')}")
            print(f"API Key: {body.get('api_key')}")
            return body.get('api_key')
        else:
            print(f"❌ Failed: {result}")
            return None
            
    except Exception as e:
        print(f"❌ Error invoking Lambda: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    create_test_api_key()

