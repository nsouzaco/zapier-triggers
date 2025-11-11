# Lambda VPC Credential Issue - Fix Implementation

## Problem Summary

Lambda functions in a VPC were returning `InvalidClientTokenId` / `UnrecognizedClientException` when calling DynamoDB and SQS, despite:
- VPC endpoints being configured (DynamoDB Gateway, SQS Interface, STS Interface)
- IAM role having correct permissions
- Security groups allowing traffic
- Retry logic being implemented

## Root Cause Analysis

### Issues Identified

1. **Inconsistent Client Creation**
   - `get_sqs_client()` and `get_dynamodb_resource()` used `boto3.Session()`
   - `get_dynamodb_client()` used `boto3.client()` directly
   - This inconsistency could cause credential loading differences

2. **No Explicit Credential Refresh**
   - When credential errors occurred, cached clients were cleared
   - However, no explicit credential refresh was triggered
   - boto3 credential provider chain wasn't being forced to re-obtain credentials

3. **Session Management**
   - No shared session management
   - Each client creation could potentially create a new session
   - No verification that credentials were actually obtained

4. **Credential Provider Chain in VPC**
   - In Lambda VPC, credentials must be obtained via STS VPC endpoint
   - boto3 should automatically use STS endpoint via private DNS (when `PrivateDnsEnabled: True`)
   - However, timing issues or credential provider chain problems could prevent this

## Solution Implemented

### 1. Standardized Client Creation

All AWS clients now use `boto3.Session()` consistently:
- `get_sqs_client()` - uses Session
- `get_dynamodb_client()` - now uses Session (was using `boto3.client()` directly)
- `get_dynamodb_resource()` - uses Session

### 2. Centralized Session Management

Added `_get_boto3_session()` function that:
- Creates a shared session with proper region configuration
- Verifies credentials are available after session creation
- Supports force refresh to create new session when needed
- Logs credential status for debugging

### 3. Explicit Credential Refresh

Added `clear_aws_clients()` function that:
- Clears all cached clients and session
- Forces complete re-initialization on next access
- Used by retry logic when credential errors occur

### 4. Enhanced Retry Logic

Updated retry logic in services:
- `QueueService.enqueue_event()` - clears clients and forces refresh on credential errors
- `EventStorageService.store_event()` - clears clients and forces refresh on credential errors
- Both services now use `_needs_refresh` flag to trigger credential refresh on next access

### 5. Better Error Handling and Logging

- Added credential verification after session creation
- Enhanced logging for credential issues
- Better error messages indicating credential refresh attempts

## Code Changes

### `app/utils/aws.py`

**Key Changes:**
- Added `_get_boto3_session()` for centralized session management
- Added `clear_aws_clients()` to force credential refresh
- Standardized all client creation to use `boto3.Session()`
- Added `force_refresh` parameter to all client getters
- Added credential verification and logging

**Before:**
```python
def get_dynamodb_client():
    _dynamodb_client = boto3.client(**client_kwargs)  # Direct client creation
```

**After:**
```python
def get_dynamodb_client(force_refresh: bool = False):
    session = _get_boto3_session(force_refresh=force_refresh)
    _dynamodb_client = session.client(**client_kwargs)  # Session-based
```

### `app/services/queue_service.py`

**Key Changes:**
- Updated retry logic to call `clear_aws_clients()`
- Added `_needs_refresh` flag to trigger credential refresh
- Enhanced logging for credential errors

### `app/services/event_storage.py`

**Key Changes:**
- Updated retry logic to call `clear_aws_clients()`
- Added `_needs_refresh` flag to trigger credential refresh
- Updated `_initialize_dynamodb()` to support force refresh
- Enhanced logging for credential errors

## How It Works

### Credential Flow in Lambda VPC

1. **Initial Client Creation:**
   - `_get_boto3_session()` creates a boto3 Session
   - boto3 credential provider chain automatically uses:
     - Lambda execution role credentials (via STS VPC endpoint)
     - STS VPC endpoint is accessed via private DNS (when `PrivateDnsEnabled: True`)
   - Credentials are verified and logged

2. **On Credential Error:**
   - Service detects `InvalidClientTokenId` or `UnrecognizedClientException`
   - Calls `clear_aws_clients()` to clear all cached clients and session
   - Sets `_needs_refresh` flag
   - Waits with exponential backoff
   - On retry, `force_refresh=True` creates new session with fresh credentials

3. **Credential Refresh:**
   - New session forces boto3 to re-obtain credentials via STS
   - STS VPC endpoint is used automatically via private DNS
   - Fresh credentials are used for the retry attempt

## Testing Recommendations

### 1. Verify VPC Endpoint Configuration

```bash
# Check STS VPC endpoint
aws ec2 describe-vpc-endpoints \
  --filters "Name=service-name,Values=com.amazonaws.us-east-1.sts" \
  --query 'VpcEndpoints[*].[VpcEndpointId,State,PrivateDnsEnabled]'

# Should show:
# - State: "available"
# - PrivateDnsEnabled: true
```

### 2. Verify Security Group Rules

```bash
# Check VPC endpoint security group allows Lambda SG
aws ec2 describe-security-groups \
  --group-ids sg-<vpc-endpoint-sg-id> \
  --query 'SecurityGroups[0].IpPermissions'

# Should allow HTTPS (443) from Lambda security group
```

### 3. Test Credential Retrieval

Add temporary logging to verify credentials:

```python
# In Lambda handler or test
import boto3
session = boto3.Session()
creds = session.get_credentials()
print(f"Credentials: {creds.access_key if creds else 'None'}")
```

### 4. Monitor CloudWatch Logs

Look for:
- "Session credentials obtained successfully" - indicates credentials are available
- "Credential error" warnings - indicates retry attempts
- "Clearing cached AWS clients" - indicates credential refresh

## Additional Troubleshooting

If the issue persists after these changes:

### 1. Verify STS VPC Endpoint DNS Resolution

In Lambda, test DNS resolution:

```python
import socket
sts_endpoint = f"sts.{region}.amazonaws.com"
try:
    ip = socket.gethostbyname(sts_endpoint)
    print(f"STS endpoint resolves to: {ip}")
except Exception as e:
    print(f"DNS resolution failed: {e}")
```

### 2. Check Route Tables

Ensure Lambda subnets have routes to VPC endpoints:

```bash
aws ec2 describe-route-tables \
  --filters "Name=vpc-id,Values=vpc-03cd6462b46350c8e" \
  --query 'RouteTables[*].Routes[?GatewayId==`vpce-*`]'
```

### 3. Verify IAM Role Permissions

Ensure Lambda role has `sts:AssumeRole` permission (should be automatic for Lambda service role).

### 4. Check Lambda Cold Start Timing

If credentials fail only on cold starts, consider:
- Adding a small delay before first AWS call
- Pre-warming Lambda functions
- Using provisioned concurrency

### 5. Explicit STS Endpoint Configuration (Advanced)

If private DNS isn't working, you can explicitly configure STS endpoint:

```python
import boto3
from botocore.config import Config

# Get STS VPC endpoint DNS name from AWS Console or CLI
sts_vpc_endpoint = "vpce-xxxxx-sts.us-east-1.vpce.amazonaws.com"

config = Config(
    region_name='us-east-1',
    # Note: This is a workaround and may not be necessary
    # boto3 should automatically use VPC endpoint via private DNS
)

session = boto3.Session()
sts_client = session.client('sts', config=config, endpoint_url=f"https://{sts_vpc_endpoint}")
```

**Note:** This should not be necessary if `PrivateDnsEnabled: True` on the STS VPC endpoint.

## Expected Behavior After Fix

1. **First Request:**
   - Session created with credentials from IAM role via STS VPC endpoint
   - Clients initialized successfully
   - Operations succeed

2. **On Credential Error:**
   - Error detected (InvalidClientTokenId/UnrecognizedClientException)
   - All clients cleared
   - Wait with exponential backoff
   - New session created with fresh credentials
   - Retry succeeds

3. **Logs Show:**
   - "Session credentials obtained successfully"
   - "SQS client created successfully" / "DynamoDB client created successfully"
   - On errors: "Credential error (attempt X/3), retrying in Ys with credential refresh..."
   - "Clearing cached AWS clients to force credential refresh"

## Next Steps

1. **Deploy the changes** to Lambda
2. **Monitor CloudWatch logs** for credential-related messages
3. **Test with actual requests** to verify DynamoDB and SQS operations
4. **If issues persist**, follow additional troubleshooting steps above

## Related Files

- `app/utils/aws.py` - AWS client utilities
- `app/services/queue_service.py` - SQS queue service
- `app/services/event_storage.py` - DynamoDB event storage
- `terraform/vpc_endpoints.tf` - VPC endpoint configuration
- `terraform/iam.tf` - IAM role and permissions

## References

- [AWS Lambda in VPC - Credentials](https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html#vpc-iam)
- [boto3 Credential Provider Chain](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html)
- [VPC Endpoints for AWS Services](https://docs.aws.amazon.com/vpc/latest/privatelink/vpc-endpoints-access.html)

