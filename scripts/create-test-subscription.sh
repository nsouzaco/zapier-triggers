#!/bin/bash
# Script to create a test subscription via the API

set -e

# Get API URL from argument or use default
API_URL="${1:-https://your-api-gateway-url.execute-api.us-east-1.amazonaws.com/Prod}"
CUSTOMER_ID="${2:-4d25b335-5197-408e-a8cd-5101d4dd6f6c}"
EVENT_TYPE="${3:-order.created}"
WEBHOOK_URL="${4:-https://webhook.site/unique-url}"

echo "🔔 Creating test subscription..."
echo "   API URL: ${API_URL}"
echo "   Customer ID: ${CUSTOMER_ID}"
echo "   Event Type: ${EVENT_TYPE}"
echo "   Webhook URL: ${WEBHOOK_URL}"
echo ""

# Create subscription
RESPONSE=$(curl -s -X POST "${API_URL}/admin/test-subscription" \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_id\": \"${CUSTOMER_ID}\",
    \"event_selector\": {
      \"type\": \"event_type\",
      \"value\": \"${EVENT_TYPE}\"
    },
    \"webhook_url\": \"${WEBHOOK_URL}\"
  }")

echo "Response:"
echo "${RESPONSE}" | python3 -m json.tool 2>/dev/null || echo "${RESPONSE}"

# Check if successful
if echo "${RESPONSE}" | grep -q "workflow_id"; then
    echo ""
    echo "✅ Subscription created successfully!"
    WORKFLOW_ID=$(echo "${RESPONSE}" | python3 -c "import sys, json; print(json.load(sys.stdin)['workflow_id'])" 2>/dev/null || echo "unknown")
    echo "   Workflow ID: ${WORKFLOW_ID}"
    echo ""
    echo "💡 Now when you send events with event_type='${EVENT_TYPE}', they will be delivered to the webhook!"
else
    echo ""
    echo "❌ Failed to create subscription"
    exit 1
fi

