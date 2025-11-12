# Code Snippets for AI Question - Lambda VPC Credential Issue

## Problem Statement

Lambda function in VPC returns `InvalidClientTokenId` / `UnrecognizedClientException` when calling DynamoDB and SQS, even though:
- VPC endpoints are configured (DynamoDB Gateway, SQS Interface, STS Interface)
- IAM role has correct permissions
- Security groups allow traffic
- Retry logic with credential refresh is implemented

**Error in logs:**
```
UnrecognizedClientException: The security token included in the request is invalid.
InvalidClientTokenId: The security token included in the request is invalid.
```

## Current AWS Client Implementation

```python
# app/utils/aws.py
import boto3
from botocore.config import Config
from app.config import get_settings
from app.utils.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

_session = None

def _get_boto3_session(force_refresh: bool = False):
    """Get or create a boto3 Session with credential refresh support."""
    global _session
    
    if _session is None or force_refresh:
        try:
            # Create a fresh session to ensure credentials are loaded from IAM role
            # In Lambda VPC, boto3 will automatically use STS VPC endpoint via private DNS
            _session = boto3.Session(region_name=settings.aws_region)
            
            # Verify credentials are available
            credentials = _session.get_credentials()
            if credentials is None:
                logger.warning("No credentials found in session.")
            else:
                if hasattr(credentials, 'access_key') and credentials.access_key:
                    logger.debug("Session credentials obtained successfully")
                    # Try to verify credentials by calling STS GetCallerIdentity
                    try:
                        sts_client = _session.client('sts', region_name=settings.aws_region)
                        sts_client.get_caller_identity()
                        logger.debug("Credentials verified via STS")
                    except Exception as sts_error:
                        logger.warning(f"STS credential verification failed: {sts_error}")
        except Exception as e:
            logger.error(f"Error creating boto3 session: {e}", exc_info=True)
            raise
    
    return _session

def clear_aws_clients():
    """Clear all cached AWS clients to force re-initialization with fresh credentials."""
    global _sqs_client, _dynamodb_client, _dynamodb_resource, _session
    logger.info("Clearing cached AWS clients to force credential refresh")
    _sqs_client = None
    _dynamodb_client = None
    _dynamodb_resource = None
    _session = None

def get_sqs_client(force_refresh: bool = False):
    """Get SQS client (lazy-initialized)."""
    global _sqs_client
    
    if _sqs_client is None or force_refresh:
        if force_refresh:
            _sqs_client = None
        
        session = _get_boto3_session(force_refresh=force_refresh)
        
        client_kwargs = {
            "service_name": "sqs",
            "region_name": settings.aws_region,
            "config": get_boto3_config(),
        }
        
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

def get_dynamodb_resource(force_refresh: bool = False):
    """Get DynamoDB resource (lazy-initialized)."""
    global _dynamodb_resource
    
    if _dynamodb_resource is None or force_refresh:
        if force_refresh:
            _dynamodb_resource = None
        
        session = _get_boto3_session(force_refresh=force_refresh)
        
        resource_kwargs = {
            "service_name": "dynamodb",
            "region_name": settings.aws_region,
            "config": get_boto3_config(),
        }
        
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            resource_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            resource_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        
        try:
            _dynamodb_resource = session.resource(**resource_kwargs)
            logger.debug("DynamoDB resource created successfully")
        except Exception as e:
            logger.error(f"Error creating DynamoDB resource: {e}", exc_info=True)
            raise
    
    return _dynamodb_resource
```

## Service Retry Logic

```python
# app/services/queue_service.py
from app.utils.aws import get_sqs_client, clear_aws_clients
from botocore.exceptions import ClientError
from time import sleep

class QueueService:
    async def enqueue_event(self, customer_id: str, event_id: str, payload: dict) -> bool:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                client = self.sqs_client
                if not client:
                    return False
                
                response = client.send_message(
                    QueueUrl=settings.sqs_event_queue_url,
                    MessageBody=json.dumps(message_body),
                    MessageAttributes=message_attributes,
                )
                
                logger.info(f"Event enqueued successfully: {event_id}")
                return True
                
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')
                if error_code in ['InvalidClientTokenId', 'UnrecognizedClientException']:
                    if attempt < max_retries - 1:
                        wait_time = 0.5 * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"Credential error (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {wait_time}s with credential refresh..."
                        )
                        sleep(wait_time)
                        # Clear all cached clients and force credential refresh
                        clear_aws_clients()
                        # Mark that we need to force refresh on next client access
                        self._needs_refresh = True
                        continue
                logger.error(f"Error enqueueing event to SQS: {e}")
                return False
```

## Infrastructure Configuration

```hcl
# terraform/vpc_endpoints.tf

# VPC Endpoint for DynamoDB (Gateway type)
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = data.aws_vpc.main.id
  service_name       = "com.amazonaws.us-east-1.dynamodb"
  vpc_endpoint_type  = "Gateway"
  route_table_ids    = data.aws_route_tables.main.ids
}

# VPC Endpoint for SQS (Interface type)
resource "aws_vpc_endpoint" "sqs" {
  vpc_id              = data.aws_vpc.main.id
  service_name         = "com.amazonaws.us-east-1.sqs"
  vpc_endpoint_type    = "Interface"
  subnet_ids           = var.subnet_ids
  security_group_ids   = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled  = true
}

# VPC Endpoint for STS (Interface type)
resource "aws_vpc_endpoint" "sts" {
  vpc_id              = data.aws_vpc.main.id
  service_name         = "com.amazonaws.us-east-1.sts"
  vpc_endpoint_type    = "Interface"
  subnet_ids           = var.subnet_ids
  security_group_ids   = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled  = true
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoint" {
  name        = "vpc-endpoint-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]  # Allow from Lambda SG
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

## Lambda Configuration

```yaml
# template.zip.yaml
Resources:
  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: zapier-triggers-api-dev-api
      Runtime: python3.11
      Handler: lambda_handler_zip.handler
      VpcConfig:
        SubnetIds:
          - subnet-0dcbb744fa27d655a
          - subnet-0ec51c4b01051563c
        SecurityGroupIds:
          - sg-0cac7dfd9f87a5989
      Role: !Ref ApiRoleArn
      Environment:
        Variables:
          ENVIRONMENT: dev
          AWS_REGION: us-east-1
          SQS_EVENT_QUEUE_URL: !Ref SqsEventQueueUrl
          DYNAMODB_TABLE_NAME: !Ref DynamoDBTableName
```

## IAM Role Configuration

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      }
    }
  ]
}
```

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:us-east-1:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## What We've Verified

1. ✅ VPC endpoints are configured and available
2. ✅ STS VPC endpoint has `PrivateDnsEnabled: True`
3. ✅ Security groups allow HTTPS (443) from Lambda SG to VPC endpoint SG
4. ✅ Lambda SG has egress to 0.0.0.0/0
5. ✅ IAM role has correct permissions
6. ✅ Retry logic clears cached clients and forces credential refresh
7. ✅ All clients use `boto3.Session()` consistently

## What Doesn't Work

- ❌ DynamoDB `PutItem` returns `UnrecognizedClientException`
- ❌ SQS `SendMessage` returns `InvalidClientTokenId`
- ❌ Retries with credential refresh still fail after 3 attempts

## What Works

- ✅ RDS connection (uses IAM database authentication, different flow)
- ✅ Health endpoint (doesn't use AWS services)
- ✅ API key authentication (RDS works)

## Question for AI

**Why are Lambda credentials invalid for DynamoDB and SQS in VPC, even though:**
1. STS VPC endpoint is configured with `PrivateDnsEnabled: True`
2. Security groups allow traffic
3. IAM role has correct permissions
4. Retry logic forces credential refresh

**What could be causing boto3 to obtain invalid credentials, and how can we fix it?**

Possible areas to investigate:
- DNS resolution for STS endpoint
- Credential provider chain in boto3
- Lambda execution environment timing
- VPC endpoint routing
- Security group configuration

