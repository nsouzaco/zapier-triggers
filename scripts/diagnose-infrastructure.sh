#!/bin/bash
# Comprehensive AWS Infrastructure Diagnostic Script
# Checks all components: VPC, NAT Gateway, Lambda, DynamoDB, RDS, SQS, etc.
# Generates a full configuration report in JSON format

set -e

REGION="${AWS_REGION:-us-east-1}"
PROJECT_NAME="${PROJECT_NAME:-zapier-triggers-api}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
OUTPUT_FILE="infrastructure-report-$(date -u +"%Y%m%d-%H%M%S").json"

echo "=========================================="
echo "AWS INFRASTRUCTURE DIAGNOSTIC REPORT"
echo "=========================================="
echo "Generated: $TIMESTAMP"
echo "Region: $REGION"
echo "Project: $PROJECT_NAME"
echo "Environment: $ENVIRONMENT"
echo "=========================================="
echo ""

# Initialize JSON report
cat > "$OUTPUT_FILE" <<EOF
{
  "timestamp": "$TIMESTAMP",
  "region": "$REGION",
  "project": "$PROJECT_NAME",
  "environment": "$ENVIRONMENT",
EOF

# Get VPC ID from Lambda functions
echo "Finding VPC ID..."
VPC_ID=$(aws lambda list-functions --region "$REGION" --query "Functions[?contains(FunctionName, '$PROJECT_NAME') && contains(FunctionName, '$ENVIRONMENT')].VpcConfig.VpcId" --output text | head -1)

if [ -z "$VPC_ID" ] || [ "$VPC_ID" == "None" ]; then
    echo "⚠️  VPC ID not found from Lambda, trying to find from VPCs..."
    VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" --query "Vpcs[0].VpcId" --output text 2>/dev/null || echo "")
fi

if [ -z "$VPC_ID" ]; then
    echo "❌ Could not determine VPC ID"
    VPC_ID="unknown"
fi

echo "VPC ID: $VPC_ID"
echo ""

# Add VPC ID to report
cat >> "$OUTPUT_FILE" <<EOF
  "vpc_id": "$VPC_ID",
EOF

# 1. VPC Information
echo "1. VPC CONFIGURATION"
echo "----------------------------------------"
VPC_INFO=$(aws ec2 describe-vpcs --region "$REGION" --vpc-ids "$VPC_ID" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
vpc = data.get('Vpcs', [{}])[0]
print(json.dumps({
    'vpc_id': vpc.get('VpcId'),
    'cidr_block': vpc.get('CidrBlock'),
    'state': vpc.get('State'),
    'enable_dns_hostnames': vpc.get('EnableDnsHostnames', False),
    'enable_dns_support': vpc.get('EnableDnsSupport', False),
    'tags': {tag['Key']: tag['Value'] for tag in vpc.get('Tags', [])}
}, indent=2))
" 2>/dev/null || echo '{"error": "Failed to get VPC info"}')
echo "$VPC_INFO"
cat >> "$OUTPUT_FILE" <<EOF
  "vpc": $VPC_INFO,
EOF
echo ""

# 2. Subnets (only those used by Lambda functions)
echo "2. SUBNETS (Project-related)"
echo "----------------------------------------"
# Get subnet IDs from Lambda functions
LAMBDA_SUBNET_IDS=$(aws lambda list-functions --region "$REGION" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
subnet_ids = set()
for func in data.get('Functions', []):
    if '$PROJECT_NAME' in func['FunctionName'] and '$ENVIRONMENT' in func['FunctionName']:
        vpc_config = func.get('VpcConfig', {})
        for sid in vpc_config.get('SubnetIds', []):
            subnet_ids.add(sid)
print(' '.join(subnet_ids))
" 2>/dev/null || echo "")

if [ -n "$LAMBDA_SUBNET_IDS" ]; then
    SUBNETS=$(aws ec2 describe-subnets --region "$REGION" --subnet-ids $LAMBDA_SUBNET_IDS 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
subnets = []
for subnet in data.get('Subnets', []):
    subnets.append({
        'subnet_id': subnet['SubnetId'],
        'cidr_block': subnet['CidrBlock'],
        'availability_zone': subnet['AvailabilityZone'],
        'map_public_ip_on_launch': subnet.get('MapPublicIpOnLaunch', False),
        'state': subnet['State'],
        'tags': {tag['Key']: tag['Value'] for tag in subnet.get('Tags', [])}
    })
print(json.dumps(subnets, indent=2))
" 2>/dev/null || echo '[]')
else
    SUBNETS='[]'
fi
echo "$SUBNETS"
cat >> "$OUTPUT_FILE" <<EOF
  "subnets": $SUBNETS,
EOF
echo ""

# 3. Route Tables (only those associated with project subnets)
echo "3. ROUTE TABLES (Project-related)"
echo "----------------------------------------"
# Get route table IDs from subnet associations
if [ -n "$LAMBDA_SUBNET_IDS" ]; then
    ROUTE_TABLE_IDS=$(aws ec2 describe-route-tables --region "$REGION" --filters "Name=association.subnet-id,Values=$(echo $LAMBDA_SUBNET_IDS | tr ' ' ',')" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
rt_ids = set()
for rt in data.get('RouteTables', []):
    rt_ids.add(rt['RouteTableId'])
print(' '.join(rt_ids))
" 2>/dev/null || echo "")
    
    if [ -n "$ROUTE_TABLE_IDS" ]; then
        ROUTE_TABLES=$(aws ec2 describe-route-tables --region "$REGION" --route-table-ids $ROUTE_TABLE_IDS 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
rts = []
for rt in data.get('RouteTables', []):
    routes = []
    for route in rt['Routes']:
        route_info = {'destination': route.get('DestinationCidrBlock', 'default'), 'state': route.get('State', 'unknown')}
        if 'GatewayId' in route:
            route_info['target'] = f\"Gateway: {route['GatewayId']}\"
        elif 'NatGatewayId' in route:
            route_info['target'] = f\"NAT Gateway: {route['NatGatewayId']}\"
        else:
            route_info['target'] = 'local'
        routes.append(route_info)
    
    associations = []
    for assoc in rt['Associations']:
        assoc_info = {'association_id': assoc.get('RouteTableAssociationId'), 'main': assoc.get('Main', False)}
        if 'SubnetId' in assoc:
            assoc_info['subnet_id'] = assoc['SubnetId']
        associations.append(assoc_info)
    
    rts.append({
        'route_table_id': rt['RouteTableId'],
        'routes': routes,
        'associations': associations,
        'tags': {tag['Key']: tag['Value'] for tag in rt.get('Tags', [])}
    })
print(json.dumps(rts, indent=2))
" 2>/dev/null || echo '[]')
    else
        ROUTE_TABLES='[]'
    fi
else
    ROUTE_TABLES='[]'
fi
echo "$ROUTE_TABLES"
cat >> "$OUTPUT_FILE" <<EOF
  "route_tables": $ROUTE_TABLES,
EOF
echo ""

# 4. NAT Gateways
echo "4. NAT GATEWAYS"
echo "----------------------------------------"
NAT_GWS=$(aws ec2 describe-nat-gateways --region "$REGION" --filter "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available,pending" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
nat_gws = []
for ngw in data.get('NatGateways', []):
    addrs = ngw.get('NatGatewayAddresses', [])
    nat_gws.append({
        'nat_gateway_id': ngw['NatGatewayId'],
        'subnet_id': ngw['SubnetId'],
        'state': ngw['State'],
        'public_ip': addrs[0].get('PublicIp') if addrs else None,
        'allocation_id': addrs[0].get('AllocationId') if addrs else None,
        'tags': {tag['Key']: tag['Value'] for tag in ngw.get('Tags', [])}
    })
print(json.dumps(nat_gws, indent=2))
" 2>/dev/null || echo '[]')
echo "$NAT_GWS"
cat >> "$OUTPUT_FILE" <<EOF
  "nat_gateways": $NAT_GWS,
EOF
echo ""

# 5. Internet Gateways
echo "5. INTERNET GATEWAYS"
echo "----------------------------------------"
IGWS=$(aws ec2 describe-internet-gateways --region "$REGION" --filters "Name=attachment.vpc-id,Values=$VPC_ID" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
igws = []
for igw in data.get('InternetGateways', []):
    igws.append({
        'internet_gateway_id': igw['InternetGatewayId'],
        'state': igw['Attachments'][0]['State'] if igw.get('Attachments') else 'unknown',
        'attached_vpcs': [a['VpcId'] for a in igw.get('Attachments', [])],
        'tags': {tag['Key']: tag['Value'] for tag in igw.get('Tags', [])}
    })
print(json.dumps(igws, indent=2))
" 2>/dev/null || echo '[]')
echo "$IGWS"
cat >> "$OUTPUT_FILE" <<EOF
  "internet_gateways": $IGWS,
EOF
echo ""

# 6. VPC Endpoints
echo "6. VPC ENDPOINTS"
echo "----------------------------------------"
VPC_ENDPOINTS=$(aws ec2 describe-vpc-endpoints --region "$REGION" --filters "Name=vpc-id,Values=$VPC_ID" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
endpoints = []
for ep in data.get('VpcEndpoints', []):
    endpoints.append({
        'vpc_endpoint_id': ep['VpcEndpointId'],
        'service_name': ep['ServiceName'],
        'vpc_endpoint_type': ep['VpcEndpointType'],
        'state': ep['State'],
        'subnet_ids': ep.get('SubnetIds', []),
        'route_table_ids': ep.get('RouteTableIds', []),
        'security_group_ids': [g['GroupId'] for g in ep.get('Groups', [])],
        'tags': {tag['Key']: tag['Value'] for tag in ep.get('Tags', [])}
    })
print(json.dumps(endpoints, indent=2))
" 2>/dev/null || echo '[]')
echo "$VPC_ENDPOINTS"
cat >> "$OUTPUT_FILE" <<EOF
  "vpc_endpoints": $VPC_ENDPOINTS,
EOF
echo ""

# 7. Security Groups (only those used by Lambda functions)
echo "7. SECURITY GROUPS (Project-related)"
echo "----------------------------------------"
# Get security group IDs from Lambda functions
LAMBDA_SG_IDS=$(aws lambda list-functions --region "$REGION" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
sg_ids = set()
for func in data.get('Functions', []):
    if '$PROJECT_NAME' in func['FunctionName'] and '$ENVIRONMENT' in func['FunctionName']:
        vpc_config = func.get('VpcConfig', {})
        for sgid in vpc_config.get('SecurityGroupIds', []):
            sg_ids.add(sgid)
print(' '.join(sg_ids))
" 2>/dev/null || echo "")

if [ -n "$LAMBDA_SG_IDS" ]; then
    SECURITY_GROUPS=$(aws ec2 describe-security-groups --region "$REGION" --group-ids $LAMBDA_SG_IDS 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
sgs = []
for sg in data.get('SecurityGroups', []):
    ingress = []
    for rule in sg.get('IpPermissions', []):
        ingress.append({
            'protocol': rule.get('IpProtocol', '-1'),
            'from_port': rule.get('FromPort'),
            'to_port': rule.get('ToPort'),
            'cidr_blocks': [ip['CidrIp'] for ip in rule.get('IpRanges', [])],
            'security_groups': [g['GroupId'] for g in rule.get('UserIdGroupPairs', [])]
        })
    
    egress = []
    for rule in sg.get('IpPermissionsEgress', []):
        egress.append({
            'protocol': rule.get('IpProtocol', '-1'),
            'from_port': rule.get('FromPort'),
            'to_port': rule.get('ToPort'),
            'cidr_blocks': [ip['CidrIp'] for ip in rule.get('IpRanges', [])],
            'security_groups': [g['GroupId'] for g in rule.get('UserIdGroupPairs', [])]
        })
    
    sgs.append({
        'security_group_id': sg['GroupId'],
        'group_name': sg['GroupName'],
        'description': sg.get('Description', ''),
        'ingress_rules': ingress,
        'egress_rules': egress,
        'tags': {tag['Key']: tag['Value'] for tag in sg.get('Tags', [])}
    })
print(json.dumps(sgs, indent=2))
" 2>/dev/null || echo '[]')
else
    SECURITY_GROUPS='[]'
fi
echo "$SECURITY_GROUPS"
cat >> "$OUTPUT_FILE" <<EOF
  "security_groups": $SECURITY_GROUPS,
EOF
echo ""

# 8. Lambda Functions
echo "8. LAMBDA FUNCTIONS"
echo "----------------------------------------"
LAMBDA_FUNCTIONS=$(aws lambda list-functions --region "$REGION" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
functions = []
for func in data.get('Functions', []):
    if '$PROJECT_NAME' in func['FunctionName'] and '$ENVIRONMENT' in func['FunctionName']:
        vpc_config = func.get('VpcConfig', {})
        functions.append({
            'function_name': func['FunctionName'],
            'runtime': func['Runtime'],
            'state': func.get('State', 'Unknown'),
            'last_update_status': func.get('LastUpdateStatus', 'Unknown'),
            'timeout': func.get('Timeout'),
            'memory_size': func.get('MemorySize'),
            'vpc_config': {
                'subnet_ids': vpc_config.get('SubnetIds', []),
                'security_group_ids': vpc_config.get('SecurityGroupIds', []),
                'vpc_id': vpc_config.get('VpcId')
            } if vpc_config else None,
            'environment_variables': func.get('Environment', {}).get('Variables', {})
        })
print(json.dumps(functions, indent=2))
" 2>/dev/null || echo '[]')
echo "$LAMBDA_FUNCTIONS"
cat >> "$OUTPUT_FILE" <<EOF
  "lambda_functions": $LAMBDA_FUNCTIONS,
EOF
echo ""

# 9. Lambda ENIs
echo "9. LAMBDA NETWORK INTERFACES (ENIs)"
echo "----------------------------------------"
LAMBDA_ENIS=$(aws ec2 describe-network-interfaces --region "$REGION" --filters "Name=description,Values=*$PROJECT_NAME*$ENVIRONMENT*" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
enis = []
for eni in data.get('NetworkInterfaces', []):
    attachment = eni.get('Attachment', {})
    enis.append({
        'network_interface_id': eni['NetworkInterfaceId'],
        'subnet_id': eni['SubnetId'],
        'private_ip': eni.get('PrivateIpAddress'),
        'status': eni['Status'],
        'description': eni.get('Description', ''),
        'attachment_id': attachment.get('AttachmentId'),
        'attachment_time': attachment.get('AttachTime').isoformat() if attachment.get('AttachTime') else None,
        'groups': [g['GroupId'] for g in eni.get('Groups', [])]
    })
print(json.dumps(enis, indent=2))
" 2>/dev/null || echo '[]')
echo "$LAMBDA_ENIS"
cat >> "$OUTPUT_FILE" <<EOF
  "lambda_enis": $LAMBDA_ENIS,
EOF
echo ""

# 10. DynamoDB Tables
echo "10. DYNAMODB TABLES"
echo "----------------------------------------"
DYNAMODB_TABLES=$(aws dynamodb list-tables --region "$REGION" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
import boto3
dynamodb = boto3.client('dynamodb', region_name='$REGION')
tables = []
for table_name in data.get('TableNames', []):
    if '$PROJECT_NAME' in table_name or 'triggers-api' in table_name:
        try:
            table_desc = dynamodb.describe_table(TableName=table_name)
            table = table_desc['Table']
            key_schema = {key['AttributeName']: key['KeyType'] for key in table['KeySchema']}
            tables.append({
                'table_name': table['TableName'],
                'status': table['TableStatus'],
                'key_schema': key_schema,
                'billing_mode': table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED'),
                'item_count': table.get('ItemCount', 0),
                'creation_date': table['CreationDateTime'].isoformat() if 'CreationDateTime' in table else None
            })
        except:
            pass
print(json.dumps(tables, indent=2))
" 2>/dev/null || echo '[]')
echo "$DYNAMODB_TABLES"
cat >> "$OUTPUT_FILE" <<EOF
  "dynamodb_tables": $DYNAMODB_TABLES,
EOF
echo ""

# 11. RDS Instances
echo "11. RDS INSTANCES"
echo "----------------------------------------"
RDS_INSTANCES=$(aws rds describe-db-instances --region "$REGION" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
instances = []
for instance in data.get('DBInstances', []):
    if '$PROJECT_NAME' in instance['DBInstanceIdentifier'] or 'triggers-api' in instance['DBInstanceIdentifier']:
        instances.append({
            'db_instance_identifier': instance['DBInstanceIdentifier'],
            'engine': instance['Engine'],
            'engine_version': instance['EngineVersion'],
            'status': instance['DBInstanceStatus'],
            'endpoint': instance.get('Endpoint', {}).get('Address'),
            'port': instance.get('Endpoint', {}).get('Port'),
            'vpc_id': instance.get('DBSubnetGroup', {}).get('VpcId'),
            'subnet_group': instance.get('DBSubnetGroup', {}).get('DBSubnetGroupName'),
            'security_groups': [sg['VpcSecurityGroupId'] for sg in instance.get('VpcSecurityGroups', [])],
            'publicly_accessible': instance.get('PubliclyAccessible', False)
        })
print(json.dumps(instances, indent=2))
" 2>/dev/null || echo '[]')
echo "$RDS_INSTANCES"
cat >> "$OUTPUT_FILE" <<EOF
  "rds_instances": $RDS_INSTANCES,
EOF
echo ""

# 12. SQS Queues
echo "12. SQS QUEUES"
echo "----------------------------------------"
SQS_QUEUES=$(aws sqs list-queues --region "$REGION" 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
import boto3
sqs = boto3.client('sqs', region_name='$REGION')
queues = []
for queue_url in data.get('QueueUrls', []):
    queue_name = queue_url.split('/')[-1]
    if '$PROJECT_NAME' in queue_name or 'triggers-api' in queue_name:
        try:
            attrs = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['All'])
            attributes = attrs['Attributes']
            queues.append({
                'queue_name': queue_name,
                'queue_url': queue_url,
                'approximate_number_of_messages': attributes.get('ApproximateNumberOfMessages', '0'),
                'approximate_number_of_messages_not_visible': attributes.get('ApproximateNumberOfMessagesNotVisible', '0'),
                'visibility_timeout': attributes.get('VisibilityTimeout'),
                'message_retention_period': attributes.get('MessageRetentionPeriod')
            })
        except:
            pass
print(json.dumps(queues, indent=2))
" 2>/dev/null || echo '[]')
echo "$SQS_QUEUES"
cat >> "$OUTPUT_FILE" <<EOF
  "sqs_queues": $SQS_QUEUES,
EOF
echo ""

# 13. Elastic IPs (only those associated with NAT Gateways)
echo "13. ELASTIC IPs (Project-related)"
echo "----------------------------------------"
# Get allocation IDs from NAT Gateways
NAT_EIP_IDS=$(echo "$NAT_GWS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
eip_ids = []
for nat in data:
    if nat.get('allocation_id'):
        eip_ids.append(nat['allocation_id'])
print(' '.join(eip_ids))
" 2>/dev/null || echo "")

if [ -n "$NAT_EIP_IDS" ]; then
    ELASTIC_IPS=$(aws ec2 describe-addresses --region "$REGION" --allocation-ids $NAT_EIP_IDS 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
eips = []
for eip in data.get('Addresses', []):
    eips.append({
        'allocation_id': eip.get('AllocationId'),
        'public_ip': eip.get('PublicIp'),
        'domain': eip.get('Domain'),
        'association_id': eip.get('AssociationId'),
        'instance_id': eip.get('InstanceId'),
        'network_interface_id': eip.get('NetworkInterfaceId')
    })
print(json.dumps(eips, indent=2))
" 2>/dev/null || echo '[]')
else
    ELASTIC_IPS='[]'
fi
echo "$ELASTIC_IPS"
cat >> "$OUTPUT_FILE" <<EOF
  "elastic_ips": $ELASTIC_IPS
}
EOF

echo ""
echo "=========================================="
echo "✅ Full report saved to: $OUTPUT_FILE"
echo "=========================================="
echo ""
echo "You can now share this JSON file with another AI for analysis."

