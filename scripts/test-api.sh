#!/bin/bash

# Test script for Zapier Triggers API
# Usage: ./scripts/test-api.sh [API_URL]

set -euo pipefail

# Get API URL from argument or use default
API_URL="${1:-https://qvl62b4mhh.execute-api.us-east-1.amazonaws.com/Prod}"

echo "🧪 Testing Zapier Triggers API"
echo "API URL: ${API_URL}"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${API_URL}/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$HEALTH_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "Response: $BODY"
else
    echo -e "${RED}❌ Health check failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
fi
echo ""

# Test 2: Root Endpoint
echo -e "${YELLOW}Test 2: Root Endpoint${NC}"
ROOT_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${API_URL}/")
HTTP_CODE=$(echo "$ROOT_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$ROOT_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ Root endpoint passed${NC}"
    echo "Response: $BODY"
else
    echo -e "${RED}❌ Root endpoint failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
fi
echo ""

# Test 3: API Documentation (if available)
echo -e "${YELLOW}Test 3: API Documentation${NC}"
DOCS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${API_URL}/docs")
HTTP_CODE=$(echo "$DOCS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ API docs available at ${API_URL}/docs${NC}"
else
    echo -e "${YELLOW}⚠️  API docs not available (HTTP $HTTP_CODE)${NC}"
fi
echo ""

# Test 4: Events Endpoint (without auth - should fail)
echo -e "${YELLOW}Test 4: Events Endpoint (No Auth)${NC}"
EVENTS_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"event_type":"test.event","payload":{"test":"data"}}' \
    "${API_URL}/api/v1/events")
HTTP_CODE=$(echo "$EVENTS_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$EVENTS_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✅ Authentication required (expected)${NC}"
    echo "Response: $BODY"
else
    echo -e "${YELLOW}⚠️  Unexpected response (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
fi
echo ""

# Test 5: Inbox Endpoint (without auth - should fail)
echo -e "${YELLOW}Test 5: Inbox Endpoint (No Auth)${NC}"
INBOX_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${API_URL}/api/v1/inbox")
HTTP_CODE=$(echo "$INBOX_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
BODY=$(echo "$INBOX_RESPONSE" | sed '/HTTP_CODE/d')

if [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
    echo -e "${GREEN}✅ Authentication required (expected)${NC}"
    echo "Response: $BODY"
else
    echo -e "${YELLOW}⚠️  Unexpected response (HTTP $HTTP_CODE)${NC}"
    echo "Response: $BODY"
fi
echo ""

echo -e "${GREEN}✅ Testing complete!${NC}"
echo ""
echo "📋 Next Steps:"
echo "  1. Set up API keys for authentication"
echo "  2. Test authenticated endpoints"
echo "  3. Monitor CloudWatch logs"
echo "  4. Check Lambda function metrics"




