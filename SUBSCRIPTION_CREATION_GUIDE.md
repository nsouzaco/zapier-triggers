# Subscription Creation Guide

## Summary

I've added functionality to create test subscriptions, but **the code needs to be deployed first** before you can use it.

## What Was Added

### 1. New Admin Endpoint
Added `/admin/test-subscription` endpoint in `app/main.py` that allows creating test subscriptions (dev mode only).

**Endpoint:** `POST /admin/test-subscription`

**Request Body:**
```json
{
  "customer_id": "4d25b335-5197-408e-a8cd-5101d4dd6f6c",
  "event_selector": {
    "type": "event_type",
    "value": "order.created"
  },
  "webhook_url": "https://webhook.site/unique-url"
}
```

### 2. Scripts Created
- `scripts/create-subscription-via-lambda.py` - Creates subscription via Lambda invocation
- `scripts/create-test-subscription.sh` - Bash script wrapper

## Current Status

❌ **Not Deployed Yet** - The endpoint returns 404 because the updated code hasn't been deployed to Lambda.

## Next Steps

### Option 1: Deploy Updated Code (Recommended)

1. **Build and deploy the updated Lambda function:**
   ```bash
   # Build function zip
   ./scripts/build-function-zip.sh
   
   # Deploy (if using SAM)
   sam deploy --template-file template.zip.yaml --stack-name zapier-triggers-api-dev
   ```

2. **After deployment, create a subscription:**
   ```bash
   # Get your API URL first
   export API_URL="https://your-api-id.execute-api.us-east-1.amazonaws.com/Prod"
   
   # Create subscription
   curl -X POST "${API_URL}/admin/test-subscription" \
     -H "Content-Type: application/json" \
     -d '{
       "customer_id": "4d25b335-5197-408e-a8cd-5101d4dd6f6c",
       "event_selector": {
         "type": "event_type",
         "value": "order.created"
       },
       "webhook_url": "https://webhook.site/your-unique-url"
     }'
   ```

### Option 2: Use Lambda Invocation (After Deployment)

```bash
python scripts/create-subscription-via-lambda.py \
  --customer-id "4d25b335-5197-408e-a8cd-5101d4dd6f6c" \
  --event-type "order.created" \
  --webhook-url "https://webhook.site/your-unique-url"
```

### Option 3: Direct Database Insert (If You Have RDS Access)

If you have direct access to RDS (via AWS CloudShell, VPN, or bastion host), you can insert directly:

```sql
INSERT INTO subscriptions (workflow_id, customer_id, event_selector, webhook_url, status, created_at, updated_at)
VALUES (
  gen_random_uuid(),
  '4d25b335-5197-408e-a8cd-5101d4dd6f6c',
  '{"type": "event_type", "value": "order.created"}'::jsonb,
  'https://webhook.site/your-unique-url',
  'active',
  NOW(),
  NOW()
);
```

## Testing After Creation

Once a subscription is created:

1. **Send a test event:**
   ```bash
   curl -X POST "${API_URL}/api/v1/events" \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "payload": {
         "event_type": "order.created",
         "order_id": "12345",
         "amount": 99.99
       }
     }'
   ```

2. **Check the event status** - Should be "delivered" instead of "unmatched"

3. **Check your webhook URL** - You should see the event payload delivered

## Event Selector Examples

### Match by Event Type
```json
{
  "type": "event_type",
  "value": "order.created"
}
```

### Match by JSONPath
```json
{
  "type": "jsonpath",
  "expression": "$.event_type == 'order.created'"
}
```

### Match by Custom Field
```json
{
  "type": "custom",
  "function": {
    "field": "amount",
    "operator": "greater_than",
    "value": 100
  }
}
```

## Webhook URL Options

For testing, you can use:
- **webhook.site** - https://webhook.site (get a unique URL)
- **RequestBin** - https://requestbin.com
- **Your own test server** - Any HTTP endpoint that accepts POST requests

## Verification

After creating a subscription, verify it exists:

```bash
# Check worker logs - should show "Found 1 subscriptions" instead of "Found 0"
aws logs tail /aws/lambda/zapier-triggers-api-dev-worker --follow
```

Or use the check script (after deployment):
```bash
python scripts/check-subscriptions.py
```

