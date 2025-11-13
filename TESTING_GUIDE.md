# Testing Guide - RDS-Only Configuration

## Overview

Since the application uses **AWS RDS only** (no local database), here are the best ways to test:

## 🎯 Recommended Testing Methods

### Method 1: Test via Deployed Lambda API (Best Option)

The Lambda function can connect to RDS, so this is the most reliable way to test.

#### Step 1: Get Your API Endpoint

```bash
# Get Lambda API Gateway URL from Terraform
cd terraform
terraform output api_gateway_url

# Or check AWS Console:
# API Gateway → Your API → Stages → Prod → Invoke URL
```

#### Step 2: Get a Valid API Key

```bash
# List API keys that exist in RDS (from Lambda logs or CloudShell)
# Known working keys from Lambda:
# - WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP
# - b5U0hmUcxuSpKk7p0a1bU04XaQQCQuIh
```

#### Step 3: Test the API

```bash
# Set your API endpoint and key
export API_URL="https://4256sf6wc3.execute-api.us-east-1.amazonaws.com/Prod"
export API_KEY="WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP"

# Test 1: Health Check
curl "${API_URL}/health"

# Test 2: Submit an Event
curl -X POST "${API_URL}/api/v1/events" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "event_type": "order.created",
      "order_id": "test-123",
      "amount": 99.99,
      "customer_email": "test@example.com"
    }
  }' | python3 -m json.tool

# Test 3: Check Inbox
curl "${API_URL}/api/v1/inbox" \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool
```

#### Step 4: Use the Test Script

```bash
# Test all endpoints
./scripts/test-api.sh "${API_URL}"

# Or with API key for authenticated tests
API_KEY="WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP" \
API_URL="${API_URL}" \
./scripts/test-api.sh "${API_URL}"
```

---

### Method 2: Test Configuration Locally

Verify that your local configuration is correct (even if you can't connect to RDS):

```bash
# Activate virtual environment
source venv/bin/activate

# Test configuration
python -c "
from app.config import get_settings
settings = get_settings()
print('✅ RDS Endpoint:', settings.rds_endpoint)
print('✅ RDS Database:', settings.rds_database)
print('✅ RDS Username:', settings.rds_username)
try:
    db_url = settings.postgresql_url
    safe_url = db_url.split('@')[1] if '@' in db_url else db_url
    print('✅ PostgreSQL URL: postgresql://***@' + safe_url)
    if 'localhost' in db_url:
        print('❌ ERROR: Using localhost!')
    else:
        print('✅ Configuration correct - using RDS')
except ValueError as e:
    print('❌ Error:', e)
"
```

---

### Method 3: Test via Frontend (If Available)

If you have the frontend running:

```bash
# Start frontend
cd frontend
npm run dev

# Open browser to http://localhost:5173
# Enter API key: WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP
# Enter API URL: https://4256sf6wc3.execute-api.us-east-1.amazonaws.com/Prod
# Test submitting events via the UI
```

---

### Method 4: Test via AWS CloudShell

If you have AWS CloudShell access, you can test directly from there:

```bash
# In AWS CloudShell
# 1. Clone your repo or upload test script
# 2. Set environment variables
export API_URL="https://4256sf6wc3.execute-api.us-east-1.amazonaws.com/Prod"
export API_KEY="WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP"

# 3. Test
curl -X POST "${API_URL}/api/v1/events" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"payload":{"event_type":"test.event","test":"data"}}'
```

---

## 🔍 Quick Test Commands

### Test Health Endpoint

```bash
curl https://4256sf6wc3.execute-api.us-east-1.amazonaws.com/Prod/health
```

### Test Events Endpoint (with auth)

```bash
API_KEY="WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP"
API_URL="https://4256sf6wc3.execute-api.us-east-1.amazonaws.com/Prod"

curl -X POST "${API_URL}/api/v1/events" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "payload": {
      "event_type": "order.created",
      "order_id": "test-$(date +%s)",
      "amount": 99.99
    }
  }' | python3 -m json.tool
```

### Test Inbox Endpoint

```bash
API_KEY="WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP"
API_URL="https://4256sf6wc3.execute-api.us-east-1.amazonaws.com/Prod"

curl "${API_URL}/api/v1/inbox" \
  -H "Authorization: Bearer ${API_KEY}" | python3 -m json.tool
```

### Test Invalid API Key (should fail)

```bash
API_URL="https://4256sf6wc3.execute-api.us-east-1.amazonaws.com/Prod"

curl -X POST "${API_URL}/api/v1/events" \
  -H "Authorization: Bearer invalid-key-123" \
  -H "Content-Type: application/json" \
  -d '{"payload":{"test":"data"}}'
# Expected: 401 Unauthorized
```

---

## 📊 Monitor Tests

### View Lambda Logs

```bash
# Get recent logs
aws logs tail /aws/lambda/zapier-triggers-api --follow

# Or view in AWS Console:
# CloudWatch → Log Groups → /aws/lambda/zapier-triggers-api
```

### Check API Gateway Metrics

```bash
# View API Gateway metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApiGateway \
  --metric-name Count \
  --dimensions Name=ApiName,Value=zapier-triggers-api \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

---

## 🧪 Automated Testing Script

Use the provided test script:

```bash
# Make it executable
chmod +x scripts/test-api.sh

# Run tests
./scripts/test-api.sh https://4256sf6wc3.execute-api.us-east-1.amazonaws.com/Prod
```

---

## ⚠️ Important Notes

1. **Local Connection**: Your local machine **cannot** connect to RDS directly (it's in a private subnet). This is expected.

2. **Use Lambda**: The best way to test is via the deployed Lambda API, which has VPC access to RDS.

3. **API Keys**: Use the API keys that Lambda can see:
   - `WRZnbWDW8VVO9HeGf2w3JKSYkF6jF2XP`
   - `b5U0hmUcxuSpKk7p0a1bU04XaQQCQuIh`

4. **Configuration**: Your local config is correct - it will use RDS when accessible (from Lambda).

---

## 🐛 Troubleshooting

### "Invalid API key" Error

- **Check**: API key exists in RDS
- **Check**: Lambda can connect to RDS (check CloudWatch logs)
- **Check**: API key is active status in database

### "Connection timeout" from Local Machine

- **Expected**: RDS is in private subnet
- **Solution**: Test via Lambda API, not directly

### "RDS configuration is required" Error

- **Check**: `.env` file has `RDS_ENDPOINT`, `RDS_USERNAME`, `RDS_PASSWORD`
- **Check**: Environment variables are loaded

---

## ✅ Success Criteria

Your tests are successful if:

1. ✅ Health endpoint returns 200
2. ✅ Events endpoint accepts authenticated requests
3. ✅ Events endpoint rejects unauthenticated requests (401)
4. ✅ Inbox endpoint returns events for authenticated requests
5. ✅ CloudWatch logs show successful database connections
6. ✅ Events are stored in DynamoDB (check AWS Console)

