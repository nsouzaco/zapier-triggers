#!/bin/bash
# Script to monitor NAT Gateway limit and create when available

REGION="us-east-1"
SUBNET_ID="subnet-0dcbb744fa27d655a"
EIP_ID="eipalloc-0a2c5c558256a44f0"
VPC_ID="vpc-03cd6462b46350c8e"
ROUTE_TABLE_ID="rtb-0a6d80ef011971490"

echo "Monitoring NAT Gateway limit..."
echo "Will attempt to create NAT Gateway when limit allows"
echo ""

while true; do
    # Check if we can create NAT Gateway
    NAT_COUNT=$(aws ec2 describe-nat-gateways --region $REGION --query 'length(NatGateways[?State==`available` || State==`pending`])' --output text)
    
    if [ "$NAT_COUNT" -lt 5 ]; then
        echo "✅ Limit allows creation (current: $NAT_COUNT/5)"
        echo "Creating NAT Gateway..."
        
        NAT_ID=$(aws ec2 create-nat-gateway --region $REGION --subnet-id $SUBNET_ID --allocation-id $EIP_ID --query 'NatGateway.NatGatewayId' --output text 2>&1)
        
        if [[ $NAT_ID == nat-* ]]; then
            echo "✅ NAT Gateway created: $NAT_ID"
            echo "Waiting for it to become available..."
            aws ec2 wait nat-gateway-available --region $REGION --nat-gateway-ids $NAT_ID
            
            echo "Adding route to Lambda route table..."
            aws ec2 create-route --route-table-id $ROUTE_TABLE_ID --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_ID --region $REGION
            
            echo "✅ NAT Gateway setup complete!"
            break
        else
            echo "❌ Failed: $NAT_ID"
        fi
    else
        echo "⏳ Limit still reached ($NAT_COUNT/5). Waiting 5 minutes..."
        sleep 300
    fi
done
