#!/bin/bash

# Quick test script for Zapier Triggers API with RDS
# Usage: ./scripts/quick-test.sh [API_URL] [API_KEY]

set -euo pipefail

# Default values - use environment variables or command line arguments
API_URL="${1:-${TRIGGERS_API_URL:-https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/Prod}}"
API_KEY="${2:-${TRIGGERS_API_KEY:-}}"

# Validate API key is provided
if [ -z "$API_KEY" ]; then
    echo "❌ Error: API key is required"
    echo "   Set TRIGGERS_API_KEY environment variable or pass as second argument"
    echo "   Usage: ./scripts/quick-test.sh [API_URL] [API_KEY]"
    exit 1
fi

echo "🧪 Quick Test - Zapier Triggers API"
echo "API URL: ${API_URL}"
echo "API Key: ${API_KEY:0:10}..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${API_URL}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$HEALTH_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}❌ Health check failed (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
fi
echo ""

# Test 2: Submit Event (Authenticated)
echo -e "${BLUE}Test 2: Submit Event (Authenticated)${NC}"
TIMESTAMP=$(date +%s)
EVENT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST \
    -H "Authorization: Bearer ${API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
        \"payload\": {
            \"event_type\": \"test.order.created\",
            \"order_id\": \"test-${TIMESTAMP}\",
            \"amount\": 99.99,
            \"customer_email\": \"test@example.com\",
            \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
        }
    }" \
    "${API_URL}/api/v1/events")
HTTP_CODE=$(echo "$EVENT_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$EVENT_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "202" ]; then
    echo -e "${GREEN}✅ Event submitted successfully (HTTP $HTTP_CODE)${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}❌ Event submission failed (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
fi
echo ""

# Test 3: Check Inbox
echo -e "${BLUE}Test 3: Check Inbox${NC}"
INBOX_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -H "Authorization: Bearer ${API_KEY}" \
    "${API_URL}/api/v1/inbox")
HTTP_CODE=$(echo "$INBOX_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$INBOX_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Inbox retrieved successfully${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}❌ Inbox retrieval failed (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
fi
echo ""

# Test 4: Invalid API Key (should fail)
echo -e "${BLUE}Test 4: Invalid API Key (should fail)${NC}"
INVALID_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST \
    -H "Authorization: Bearer invalid-key-12345" \
    -H "Content-Type: application/json" \
    -d '{"payload":{"test":"data"}}' \
    "${API_URL}/api/v1/events")
HTTP_CODE=$(echo "$INVALID_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$INVALID_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✅ Invalid API key correctly rejected (HTTP $HTTP_CODE)${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${YELLOW}⚠️  Unexpected response (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
fi
echo ""

# Summary
echo -e "${BLUE}=== Test Summary ===${NC}"
echo ""
echo "📋 Next Steps:"
echo "  1. Check CloudWatch logs: aws logs tail /aws/lambda/zapier-triggers-api --follow"
echo "  2. Verify events in DynamoDB (AWS Console)"
echo "  3. Check API Gateway metrics (AWS Console)"
echo ""
echo "🔑 API Key used: ${API_KEY:0:20}..."
echo ""
echo "💡 Tip: Set TRIGGERS_API_KEY environment variable to avoid passing it each time"
echo ""

