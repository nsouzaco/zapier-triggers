# Quick Question for AI - Lambda VPC Credential Issue

## Problem
Lambda in VPC gets `InvalidClientTokenId`/`UnrecognizedClientException` calling DynamoDB/SQS, despite:
- STS VPC endpoint configured (PrivateDnsEnabled: True)
- Security groups allow traffic
- IAM role has permissions
- Retry with credential refresh implemented

## Key Code Snippet - AWS Client Creation

```python
# app/utils/aws.py
import boto3

_session = None

def _get_boto3_session(force_refresh: bool = False):
    global _session
    if _session is None or force_refresh:
        # In Lambda VPC, should use STS VPC endpoint via private DNS
        _session = boto3.Session(region_name=settings.aws_region)
        credentials = _session.get_credentials()
        # Verify with STS
        try:
            sts_client = _session.client('sts', region_name=settings.aws_region)
            sts_client.get_caller_identity()  # This works
        except Exception as e:
            logger.warning(f"STS verification failed: {e}")
    return _session

def get_sqs_client(force_refresh: bool = False):
    global _sqs_client
    if _sqs_client is None or force_refresh:
        session = _get_boto3_session(force_refresh=force_refresh)
        _sqs_client = session.client('sqs', region_name=settings.aws_region)
    return _sqs_client
```

## Retry Logic

```python
# On credential error:
except ClientError as e:
    if e.response['Error']['Code'] in ['InvalidClientTokenId', 'UnrecognizedClientException']:
        clear_aws_clients()  # Clears session and all clients
        sleep(wait_time)
        # Retry - creates new session, but still gets invalid credentials
        client.send_message(...)  # Still fails
```

## Infrastructure
- VPC: vpc-03cd6462b46350c8e
- STS Endpoint: vpce-07162ab6b3b64bc37 (available, PrivateDnsEnabled: True)
- Lambda Subnets: subnet-0dcbb744fa27d655a, subnet-0ec51c4b01051563c
- Lambda SG: sg-0cac7dfd9f87a5989 (egress: 0.0.0.0/0)
- VPC Endpoint SG: sg-0664983e4ef68b208 (ingress: 443 from Lambda SG)

## What Works
- ✅ RDS connection (IAM auth)
- ✅ Health endpoint
- ✅ STS get_caller_identity() call

## What Fails
- ❌ DynamoDB PutItem → UnrecognizedClientException
- ❌ SQS SendMessage → InvalidClientTokenId

## Question
Why does boto3 get invalid credentials for DynamoDB/SQS in Lambda VPC when:
1. STS endpoint is configured correctly
2. Security groups allow traffic
3. STS get_caller_identity() works (credentials are valid)
4. But DynamoDB/SQS calls fail with invalid token errors

Is this a DNS resolution issue, credential provider chain problem, or something else?

