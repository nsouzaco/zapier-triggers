# Worker Lambda Implementation Summary & Issues

## Executive Summary

The Zapier Triggers API worker Lambda has been successfully converted from container image deployment to zip deployment, resolving the critical `Runtime.InvalidEntrypoint` error. However, the worker is currently failing to process SQS messages due to message format parsing issues. Events are being enqueued successfully but remain in "pending" status because the worker cannot parse the SQS message format correctly.

---

## Current Implementation Status

### ✅ Completed Fixes

1. **Worker Lambda Deployment Method**
   - **Before**: Container image deployment (failing with `Runtime.InvalidEntrypoint`)
   - **After**: Zip deployment with Lambda Layers (working)
   - **Status**: ✅ Deployed and running

2. **IAM Permissions**
   - Added VPC permissions to worker role:
     - `ec2:CreateNetworkInterface`
     - `ec2:DescribeNetworkInterfaces`
     - `ec2:DeleteNetworkInterface`
   - **Status**: ✅ Fixed

3. **SQS Queue**
   - Queue was deleted during stack deletion
   - Recreated via Terraform
   - **Status**: ✅ Active and receiving messages

4. **Enhanced Logging**
   - Added detailed logging throughout worker pipeline
   - **Status**: ✅ Implemented

---

## Architecture Overview

### Event Flow

```
1. API Endpoint (POST /api/v1/events)
   ↓
2. Event Storage (DynamoDB) - Status: "pending"
   ↓
3. SQS Queue (zapier-triggers-api-dev-events)
   ↓
4. Worker Lambda (triggered by SQS)
   ↓
5. Event Processor
   ↓
6. Subscription Lookup (RDS)
   ↓
7. Event Matching & Webhook Delivery
   ↓
8. Status Update (DynamoDB) - Status: "delivered"/"failed"/"unmatched"
```

### Current Components

**API Lambda** (`zapier-triggers-api-dev-api`)
- Runtime: Python 3.11
- Deployment: Zip + Lambda Layer
- Handler: `lambda_handler_zip.handler`
- Status: ✅ Working

**Worker Lambda** (`zapier-triggers-api-dev-worker`)
- Runtime: Python 3.11
- Deployment: Zip + Lambda Layer
- Handler: `lambda_worker_zip.handler`
- Trigger: SQS EventSourceMapping
- Status: ⚠️ Running but failing to process messages

---

## Current Issues

### Issue #1: SQS Message Format Parsing Error

**Problem**: The worker is receiving SQS messages but failing to parse them correctly.

**Error Logs**:
```
[ERROR] Invalid message format: {'Body': {}}
[ERROR] Missing fields - customer_id: False, event_id: False, payload: False
```

**Root Cause**: The SQS message format from the EventSourceMapping is different from what the worker expects.

**Current Code** (`app/workers/event_processor.py`):
```python
async def process_message(self, sqs_message: Dict[str, Any]) -> bool:
    try:
        logger.info(f"Starting to process event. Message keys: {list(message.keys())}")
        
        # Parse message body
        if isinstance(message.get("Body"), str):
            body = json.loads(message["Body"])
        else:
            body = message.get("Body", {})

        customer_id = body.get("customer_id")
        event_id = body.get("event_id")
        payload = body.get("payload")
```

**Problem**: When SQS triggers Lambda via EventSourceMapping, the message structure is:
```json
{
  "Records": [
    {
      "messageId": "...",
      "body": "{\"customer_id\":\"...\",\"event_id\":\"...\",\"payload\":{...}}",
      "attributes": {...},
      "messageAttributes": {...}
    }
  ]
}
```

But `process_message` is being called with the individual record, which has `body` (lowercase) not `Body` (uppercase), and the body is a JSON string that needs parsing.

**Expected Flow**:
1. `lambda_worker_zip.handler` receives `{"Records": [...]}`
2. Calls `event_processor.process_message(record)` for each record
3. `process_message` should extract `record["body"]` (string) and parse it
4. But it's looking for `message.get("Body")` which doesn't exist

**Code Location**: `app/workers/event_processor.py:150-169`

---

### Issue #2: Message Body Extraction

**Current Implementation** (`lambda_worker_zip.py`):
```python
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info(f"Received SQS event with {len(event.get('Records', []))} records")
    
    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")
        try:
            logger.info(f"Processing message: {message_id}")
            logger.debug(f"Message body: {record.get('body', 'N/A')[:200]}")
            
            # Process message synchronously
            success = asyncio.run(event_processor.process_message(record))
```

**Problem**: The handler passes the raw SQS record to `process_message`, but `process_message` expects a different format with a `Body` key.

**What's Happening**:
- SQS record has: `{"messageId": "...", "body": "{...}", ...}`
- `process_message` expects: `{"Body": "{...}"}`
- Result: `body` is `{}` (empty dict) because it's looking for the wrong key

---

### Issue #3: Database Connection (Potential)

**Observation**: When testing locally, RDS connection times out:
```
PostgreSQL not available: (psycopg2.OperationalError) connection to server at 
"zapier-triggers-api-dev-postgres.crws0amqe1e3.us-east-1.rds.amazonaws.com" 
(172.31.11.207), port 5432 failed: Operation timed out
```

**Status**: This is expected for local testing (RDS is in private subnet). The Lambda should be able to connect via VPC, but we haven't verified this yet because Issue #1 prevents us from reaching the database connection code.

---

## Code Snippets

### Worker Handler (`lambda_worker_zip.py`)

```python
def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing SQS messages.
    """
    logger.info(f"Received SQS event with {len(event.get('Records', []))} records")
    logger.info(f"Lambda context: RequestId={context.aws_request_id}, RemainingTime={context.get_remaining_time_in_millis()}ms")
    
    results = {
        "batchItemFailures": []
    }
    
    # Process each SQS record
    for record in event.get("Records", []):
        message_id = record.get("messageId", "unknown")
        try:
            logger.info(f"Processing message: {message_id}")
            logger.debug(f"Message body: {record.get('body', 'N/A')[:200]}")
            
            # Process message synchronously
            success = asyncio.run(event_processor.process_message(record))
            
            if not success:
                results["batchItemFailures"].append({
                    "itemIdentifier": message_id
                })
                logger.warning(f"Failed to process message: {message_id}")
            else:
                logger.info(f"Successfully processed message: {message_id}")
                
        except Exception as e:
            logger.error(f"Error processing record {message_id}: {e}", exc_info=True)
            results["batchItemFailures"].append({
                "itemIdentifier": message_id
            })
    
    return results
```

**Issue**: Passes raw SQS record directly to `process_message`, but the format doesn't match.

---

### Event Processor (`app/workers/event_processor.py`)

```python
async def process_message(self, sqs_message: Dict[str, Any]) -> bool:
    """
    Process an SQS message.
    """
    try:
        logger.info(f"Starting to process event. Message keys: {list(message.keys())}")
        
        # Parse message body
        if isinstance(message.get("Body"), str):
            body = json.loads(message["Body"])
        else:
            body = message.get("Body", {})

        customer_id = body.get("customer_id")
        event_id = body.get("event_id")
        payload = body.get("payload")

        if not customer_id or not event_id or not payload:
            logger.error(f"Invalid message format: {message}")
            logger.error(f"Missing fields - customer_id: {customer_id is not None}, event_id: {event_id is not None}, payload: {payload is not None}")
            return False
```

**Issue**: 
- Looks for `message.get("Body")` (uppercase) but SQS record has `"body"` (lowercase)
- When `Body` doesn't exist, `body` becomes `{}` (empty dict)
- Then `body.get("customer_id")` returns `None`

**Expected SQS Record Format**:
```json
{
  "messageId": "abc123",
  "body": "{\"customer_id\":\"4d25b335-...\",\"event_id\":\"...\",\"payload\":{...}}",
  "attributes": {...},
  "messageAttributes": {...}
}
```

---

### Queue Service (`app/services/queue_service.py`)

```python
async def enqueue_event(
    self,
    customer_id: str,
    event_id: str,
    payload: dict,
) -> bool:
    # ... message construction ...
    
    message_body = {
        "customer_id": customer_id,
        "event_id": event_id,
        "payload": payload,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    # ... retry logic ...
    
    response = client.send_message(
        QueueUrl=settings.sqs_event_queue_url,
        MessageBody=json.dumps(message_body),  # JSON string
        MessageAttributes=message_attributes,
    )
```

**Status**: ✅ Working correctly - messages are being enqueued as JSON strings.

---

## Error Flow Analysis

### Current Error Path

1. **SQS Message Structure** (from EventSourceMapping):
   ```json
   {
     "Records": [
       {
         "messageId": "abc123",
         "body": "{\"customer_id\":\"...\",\"event_id\":\"...\",\"payload\":{...}}",
         ...
       }
     ]
   }
   ```

2. **Handler receives event** → Extracts `Records` array ✅

3. **Handler calls `process_message(record)`** → Passes individual record ✅

4. **`process_message` looks for `message.get("Body")`** → ❌ Doesn't exist (it's `"body"`)

5. **Falls back to `message.get("Body", {})`** → Returns `{}` ❌

6. **Tries to extract `body.get("customer_id")`** → Returns `None` ❌

7. **Validation fails** → Returns `False` ❌

8. **Message added to batch failures** → Will retry ❌

---

## Fix Required

### Solution: Fix Message Body Extraction

**File**: `app/workers/event_processor.py`

**Current Code** (`app/workers/event_processor.py` lines 176-185):
```python
async def process_message(self, sqs_message: Dict[str, Any]) -> bool:
    try:
        # Extract message body
        message_body = sqs_message.get("Body", "{}")  # ❌ Looking for "Body" (uppercase)
        # But SQS EventSourceMapping provides "body" (lowercase)!
        if isinstance(message_body, str):
            message = {"Body": json.loads(message_body)}
        else:
            message = {"Body": message_body}  # ❌ message_body is None, so message = {"Body": None}
        
        # Process event
        success = await self.process_event(message)
        return success
```

**Then in `process_event`** (lines 46-66):
```python
async def process_event(self, message: Dict[str, Any]) -> bool:
    try:
        logger.info(f"Starting to process event. Message keys: {list(message.keys())}")
        
        # Parse message body
        if isinstance(message.get("Body"), str):
            body = json.loads(message["Body"])
        else:
            body = message.get("Body", {})  # ❌ Returns {} when "Body" is None
        
        customer_id = body.get("customer_id")  # ❌ None (because body is {})
        event_id = body.get("event_id")        # ❌ None
        payload = body.get("payload")          # ❌ None
        
        if not customer_id or not event_id or not payload:
            logger.error(f"Invalid message format: {message}")
            return False
```

**Fixed Code**:
```python
# Parse message body
# SQS EventSourceMapping provides "body" (lowercase) as a JSON string
message_body = sqs_message.get("body")
if isinstance(message_body, str):
    body = json.loads(message_body)
elif isinstance(message_body, dict):
    body = message_body
else:
    # Fallback: try "Body" for backwards compatibility
    message_body = sqs_message.get("Body")
    if isinstance(message_body, str):
        body = json.loads(message_body)
    else:
        body = message_body or {}
```

**Or simpler**:
```python
# SQS EventSourceMapping provides "body" (lowercase) as a JSON string
body_str = sqs_message.get("body") or sqs_message.get("Body", "{}")
if isinstance(body_str, str):
    body = json.loads(body_str)
else:
    body = body_str or {}
```

---

## Testing Status

### ✅ Working
- API endpoint accepts events
- Events stored in DynamoDB
- Events enqueued to SQS
- Worker Lambda deployed and running
- SQS trigger configured and enabled
- Worker receives SQS events

### ❌ Not Working
- Worker cannot parse SQS message body
- Events remain in "pending" status
- No events processed successfully

### ⚠️ Unknown
- RDS connection from Lambda (blocked by Issue #1)
- Subscription lookup (blocked by Issue #1)
- Event matching logic (blocked by Issue #1)
- Webhook delivery (blocked by Issue #1)

---

## Next Steps

1. **Fix Message Parsing** (Priority 1)
   - Update `process_message` to handle SQS EventSourceMapping format
   - Test with manual invocation
   - Verify events are processed

2. **Verify RDS Connection** (Priority 2)
   - Once message parsing works, check if worker can connect to RDS
   - Verify subscription lookup works
   - Test with/without subscriptions

3. **End-to-End Testing** (Priority 3)
   - Submit event via API
   - Verify worker processes it
   - Check status changes from "pending" to "unmatched"/"delivered"/"failed"
   - Verify inbox shows updated status

4. **Create Test Subscription** (Priority 4)
   - Add subscription to database
   - Test event matching
   - Test webhook delivery

---

## Queue Status

**Current State**:
- Messages in queue: 2
- Messages being processed: 0
- Messages in DLQ: 8 (from previous failures)

**Expected After Fix**:
- Messages processed successfully
- Status updated in DynamoDB
- Events move from "pending" to final status

---

## Configuration

### Worker Lambda Configuration
```json
{
  "FunctionName": "zapier-triggers-api-dev-worker",
  "Runtime": "python3.11",
  "Handler": "lambda_worker_zip.handler",
  "PackageType": "Zip",
  "Timeout": 300,
  "MemorySize": 1024,
  "VpcConfig": {
    "SubnetIds": ["subnet-0dcbb744fa27d655a", "subnet-0ec51c4b01051563c"],
    "SecurityGroupIds": ["sg-0cac7dfd9f87a5989"]
  }
}
```

### SQS EventSourceMapping
```json
{
  "UUID": "2ccdbdfc-3577-4314-ba6d-dccbd3a87ba5",
  "State": "Enabled",
  "BatchSize": 10,
  "MaximumBatchingWindowInSeconds": 5,
  "EventSourceArn": "arn:aws:sqs:us-east-1:971422717446:zapier-triggers-api-dev-events"
}
```

---

## Summary

The worker Lambda has been successfully converted to zip deployment and is receiving SQS messages. However, a critical bug in message parsing prevents events from being processed. The fix is straightforward - update the message body extraction to handle the SQS EventSourceMapping format correctly. Once fixed, the worker should be able to process events and update their status accordingly.

**Status**: 🟡 **Partially Working** - Infrastructure is correct, but message parsing needs fixing.

