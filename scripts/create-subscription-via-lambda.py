#!/usr/bin/env python3
"""Create a test subscription by invoking the Lambda function."""

import json
import boto3
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def create_subscription_via_lambda(
    customer_id: str = "4d25b335-5197-408e-a8cd-5101d4dd6f6c",
    event_type: str = "order.created",
    webhook_url: str = "https://webhook.site/unique-url",
    api_url: str = None
):
    """Create a subscription by calling the API endpoint."""
    
    if api_url:
        # Use direct HTTP call if API URL provided
        import urllib.request
        import urllib.parse
        
        data = json.dumps({
            "customer_id": customer_id,
            "event_selector": {
                "type": "event_type",
                "value": event_type
            },
            "webhook_url": webhook_url
        }).encode('utf-8')
        
        req = urllib.request.Request(
            f"{api_url}/admin/test-subscription",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                print(f"Response Status: {response.status}")
                print(f"Response: {json.dumps(response_data, indent=2)}")
                return response_data
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"❌ HTTP Error {e.code}: {error_body}")
            return None
    else:
        # Use Lambda invocation (API Gateway event format)
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        payload = {
            "resource": "/admin/test-subscription",
            "path": "/admin/test-subscription",
            "httpMethod": "POST",
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            "multiValueHeaders": {},
            "queryStringParameters": None,
            "multiValueQueryStringParameters": None,
            "pathParameters": None,
            "stageVariables": None,
            "requestContext": {
                "resourceId": "test",
                "resourcePath": "/admin/test-subscription",
                "httpMethod": "POST",
                "requestId": "test-request-id",
                "path": "/Prod/admin/test-subscription",
                "accountId": "123456789012",
                "protocol": "HTTP/1.1",
                "stage": "Prod",
                "requestTime": "09/Apr/2015:12:34:56 +0000",
                "requestTimeEpoch": 1428582896000,
                "identity": {
                    "cognitoIdentityPoolId": None,
                    "accountId": None,
                    "cognitoIdentityId": None,
                    "caller": None,
                    "sourceIp": "127.0.0.1",
                    "accessKey": None,
                    "cognitoAuthenticationType": None,
                    "cognitoAuthenticationProvider": None,
                    "userArn": None,
                    "userAgent": "Custom User Agent String",
                    "user": None
                },
                "apiId": "test-api-id"
            },
            "body": json.dumps({
                "customer_id": customer_id,
                "event_selector": {
                    "type": "event_type",
                    "value": event_type
                },
                "webhook_url": webhook_url
            }),
            "isBase64Encoded": False
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
                print(f"\n✅ Subscription created!")
                print(f"   Workflow ID: {body.get('workflow_id')}")
                print(f"   Customer ID: {body.get('customer_id')}")
                print(f"   Event Selector: {body.get('event_selector')}")
                return body
            else:
                print(f"❌ Failed: {result}")
                return None
                
        except Exception as e:
            print(f"❌ Error invoking Lambda: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create a test subscription")
    parser.add_argument("--customer-id", default="4d25b335-5197-408e-a8cd-5101d4dd6f6c", help="Customer ID")
    parser.add_argument("--event-type", default="order.created", help="Event type to match")
    parser.add_argument("--webhook-url", default="https://webhook.site/unique-url", help="Webhook URL")
    parser.add_argument("--api-url", help="API Gateway URL (if provided, uses HTTP instead of Lambda invocation)")
    
    args = parser.parse_args()
    
    create_subscription_via_lambda(
        customer_id=args.customer_id,
        event_type=args.event_type,
        webhook_url=args.webhook_url,
        api_url=args.api_url
    )

