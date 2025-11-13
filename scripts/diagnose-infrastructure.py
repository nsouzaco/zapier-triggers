#!/usr/bin/env python3
"""
Comprehensive AWS Infrastructure Diagnostic Script
Checks all components: VPC, NAT Gateway, Lambda, DynamoDB, RDS, SQS, etc.
Generates a full configuration report.
"""

import json
import boto3
from datetime import datetime
from typing import Dict, List, Any

# Configuration
REGION = "us-east-1"
PROJECT_NAME = "zapier-triggers-api"
ENVIRONMENT = "dev"

def get_vpc_info(ec2_client, vpc_id: str) -> Dict[str, Any]:
    """Get VPC information."""
    try:
        vpcs = ec2_client.describe_vpcs(VpcIds=[vpc_id])
        if vpcs['Vpcs']:
            vpc = vpcs['Vpcs'][0]
            return {
                "vpc_id": vpc['VpcId'],
                "cidr_block": vpc['CidrBlock'],
                "state": vpc['State'],
                "enable_dns_hostnames": vpc.get('EnableDnsHostnames', False),
                "enable_dns_support": vpc.get('EnableDnsSupport', False),
                "tags": {tag['Key']: tag['Value'] for tag in vpc.get('Tags', [])}
            }
    except Exception as e:
        return {"error": str(e)}
    return {}

def get_subnets(ec2_client, vpc_id: str) -> List[Dict[str, Any]]:
    """Get all subnets in VPC."""
    try:
        subnets = ec2_client.describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        result = []
        for subnet in subnets['Subnets']:
            result.append({
                "subnet_id": subnet['SubnetId'],
                "cidr_block": subnet['CidrBlock'],
                "availability_zone": subnet['AvailabilityZone'],
                "map_public_ip_on_launch": subnet.get('MapPublicIpOnLaunch', False),
                "state": subnet['State'],
                "tags": {tag['Key']: tag['Value'] for tag in subnet.get('Tags', [])}
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_route_tables(ec2_client, vpc_id: str) -> List[Dict[str, Any]]:
    """Get all route tables in VPC."""
    try:
        rts = ec2_client.describe_route_tables(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        result = []
        for rt in rts['RouteTables']:
            routes = []
            for route in rt['Routes']:
                route_info = {
                    "destination": route.get('DestinationCidrBlock', 'default'),
                    "state": route.get('State', 'unknown')
                }
                if 'GatewayId' in route:
                    route_info["target"] = f"Gateway: {route['GatewayId']}"
                elif 'NatGatewayId' in route:
                    route_info["target"] = f"NAT Gateway: {route['NatGatewayId']}"
                elif 'NetworkInterfaceId' in route:
                    route_info["target"] = f"ENI: {route['NetworkInterfaceId']}"
                else:
                    route_info["target"] = "local"
                routes.append(route_info)
            
            associations = []
            for assoc in rt['Associations']:
                assoc_info = {
                    "association_id": assoc.get('RouteTableAssociationId'),
                    "main": assoc.get('Main', False)
                }
                if 'SubnetId' in assoc:
                    assoc_info["subnet_id"] = assoc['SubnetId']
                associations.append(assoc_info)
            
            result.append({
                "route_table_id": rt['RouteTableId'],
                "routes": routes,
                "associations": associations,
                "tags": {tag['Key']: tag['Value'] for tag in rt.get('Tags', [])}
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_nat_gateways(ec2_client, vpc_id: str) -> List[Dict[str, Any]]:
    """Get NAT Gateways in VPC."""
    try:
        nat_gws = ec2_client.describe_nat_gateways(
            Filter=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'state', 'Values': ['available', 'pending']}
            ]
        )
        result = []
        for ngw in nat_gws['NatGateways']:
            addrs = ngw.get('NatGatewayAddresses', [])
            public_ip = addrs[0].get('PublicIp') if addrs else None
            result.append({
                "nat_gateway_id": ngw['NatGatewayId'],
                "subnet_id": ngw['SubnetId'],
                "state": ngw['State'],
                "public_ip": public_ip,
                "allocation_id": addrs[0].get('AllocationId') if addrs else None,
                "tags": {tag['Key']: tag['Value'] for tag in ngw.get('Tags', [])}
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_internet_gateways(ec2_client, vpc_id: str) -> List[Dict[str, Any]]:
    """Get Internet Gateways attached to VPC."""
    try:
        igws = ec2_client.describe_internet_gateways(
            Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
        )
        result = []
        for igw in igws['InternetGateways']:
            attachments = [a['VpcId'] for a in igw.get('Attachments', [])]
            result.append({
                "internet_gateway_id": igw['InternetGatewayId'],
                "state": igw['Attachments'][0]['State'] if igw.get('Attachments') else 'unknown',
                "attached_vpcs": attachments,
                "tags": {tag['Key']: tag['Value'] for tag in igw.get('Tags', [])}
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_vpc_endpoints(ec2_client, vpc_id: str) -> List[Dict[str, Any]]:
    """Get VPC Endpoints in VPC."""
    try:
        endpoints = ec2_client.describe_vpc_endpoints(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        result = []
        for ep in endpoints['VpcEndpoints']:
            result.append({
                "vpc_endpoint_id": ep['VpcEndpointId'],
                "service_name": ep['ServiceName'],
                "vpc_endpoint_type": ep['VpcEndpointType'],
                "state": ep['State'],
                "subnet_ids": ep.get('SubnetIds', []),
                "route_table_ids": ep.get('RouteTableIds', []),
                "security_group_ids": ep.get('Groups', []),
                "tags": {tag['Key']: tag['Value'] for tag in ep.get('Tags', [])}
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_security_groups(ec2_client, vpc_id: str) -> List[Dict[str, Any]]:
    """Get Security Groups in VPC."""
    try:
        sgs = ec2_client.describe_security_groups(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
        )
        result = []
        for sg in sgs['SecurityGroups']:
            ingress = []
            for rule in sg.get('IpPermissions', []):
                ingress.append({
                    "protocol": rule.get('IpProtocol', '-1'),
                    "from_port": rule.get('FromPort'),
                    "to_port": rule.get('ToPort'),
                    "cidr_blocks": [ip['CidrIp'] for ip in rule.get('IpRanges', [])],
                    "security_groups": [g['GroupId'] for g in rule.get('UserIdGroupPairs', [])]
                })
            
            egress = []
            for rule in sg.get('IpPermissionsEgress', []):
                egress.append({
                    "protocol": rule.get('IpProtocol', '-1'),
                    "from_port": rule.get('FromPort'),
                    "to_port": rule.get('ToPort'),
                    "cidr_blocks": [ip['CidrIp'] for ip in rule.get('IpRanges', [])],
                    "security_groups": [g['GroupId'] for g in rule.get('UserIdGroupPairs', [])]
                })
            
            result.append({
                "security_group_id": sg['GroupId'],
                "group_name": sg['GroupName'],
                "description": sg.get('Description', ''),
                "ingress_rules": ingress,
                "egress_rules": egress,
                "tags": {tag['Key']: tag['Value'] for tag in sg.get('Tags', [])}
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_lambda_functions(lambda_client) -> List[Dict[str, Any]]:
    """Get Lambda functions for the project."""
    try:
        functions = lambda_client.list_functions()
        result = []
        for func in functions['Functions']:
            if PROJECT_NAME in func['FunctionName'] and ENVIRONMENT in func['FunctionName']:
                vpc_config = func.get('VpcConfig', {})
                result.append({
                    "function_name": func['FunctionName'],
                    "runtime": func['Runtime'],
                    "state": func.get('State', 'Unknown'),
                    "last_update_status": func.get('LastUpdateStatus', 'Unknown'),
                    "timeout": func.get('Timeout'),
                    "memory_size": func.get('MemorySize'),
                    "vpc_config": {
                        "subnet_ids": vpc_config.get('SubnetIds', []),
                        "security_group_ids": vpc_config.get('SecurityGroupIds', []),
                        "vpc_id": vpc_config.get('VpcId')
                    } if vpc_config else None,
                    "environment_variables": func.get('Environment', {}).get('Variables', {})
                })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_lambda_enis(ec2_client, function_names: List[str]) -> List[Dict[str, Any]]:
    """Get Network Interfaces for Lambda functions."""
    try:
        enis = ec2_client.describe_network_interfaces(
            Filters=[
                {'Name': 'description', 'Values': [f'*{name}*' for name in function_names]}
            ]
        )
        result = []
        for eni in enis['NetworkInterfaces']:
            attachment = eni.get('Attachment', {})
            result.append({
                "network_interface_id": eni['NetworkInterfaceId'],
                "subnet_id": eni['SubnetId'],
                "private_ip": eni.get('PrivateIpAddress'),
                "status": eni['Status'],
                "description": eni.get('Description', ''),
                "attachment_id": attachment.get('AttachmentId'),
                "attachment_time": attachment.get('AttachTime').isoformat() if attachment.get('AttachTime') else None,
                "groups": [g['GroupId'] for g in eni.get('Groups', [])]
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_dynamodb_tables(dynamodb_client) -> List[Dict[str, Any]]:
    """Get DynamoDB tables for the project."""
    try:
        tables = dynamodb_client.list_tables()
        result = []
        for table_name in tables['TableNames']:
            if PROJECT_NAME in table_name or 'triggers-api' in table_name:
                table_desc = dynamodb_client.describe_table(TableName=table_name)
                table = table_desc['Table']
                key_schema = {key['AttributeName']: key['KeyType'] for key in table['KeySchema']}
                result.append({
                    "table_name": table['TableName'],
                    "status": table['TableStatus'],
                    "key_schema": key_schema,
                    "billing_mode": table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED'),
                    "item_count": table.get('ItemCount', 0),
                    "creation_date": table['CreationDateTime'].isoformat() if 'CreationDateTime' in table else None
                })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_rds_instances(rds_client) -> List[Dict[str, Any]]:
    """Get RDS instances for the project."""
    try:
        instances = rds_client.describe_db_instances()
        result = []
        for instance in instances['DBInstances']:
            if PROJECT_NAME in instance['DBInstanceIdentifier'] or 'triggers-api' in instance['DBInstanceIdentifier']:
                result.append({
                    "db_instance_identifier": instance['DBInstanceIdentifier'],
                    "engine": instance['Engine'],
                    "engine_version": instance['EngineVersion'],
                    "status": instance['DBInstanceStatus'],
                    "endpoint": instance.get('Endpoint', {}).get('Address'),
                    "port": instance.get('Endpoint', {}).get('Port'),
                    "vpc_id": instance.get('DBSubnetGroup', {}).get('VpcId'),
                    "subnet_group": instance.get('DBSubnetGroup', {}).get('DBSubnetGroupName'),
                    "security_groups": [sg['VpcSecurityGroupId'] for sg in instance.get('VpcSecurityGroups', [])],
                    "publicly_accessible": instance.get('PubliclyAccessible', False)
                })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_sqs_queues(sqs_client) -> List[Dict[str, Any]]:
    """Get SQS queues for the project."""
    try:
        queues = sqs_client.list_queues()
        result = []
        for queue_url in queues.get('QueueUrls', []):
            queue_name = queue_url.split('/')[-1]
            if PROJECT_NAME in queue_name or 'triggers-api' in queue_name:
                attrs = sqs_client.get_queue_attributes(
                    QueueUrl=queue_url,
                    AttributeNames=['All']
                )
                attributes = attrs['Attributes']
                result.append({
                    "queue_name": queue_name,
                    "queue_url": queue_url,
                    "approximate_number_of_messages": attributes.get('ApproximateNumberOfMessages', '0'),
                    "approximate_number_of_messages_not_visible": attributes.get('ApproximateNumberOfMessagesNotVisible', '0'),
                    "visibility_timeout": attributes.get('VisibilityTimeout'),
                    "message_retention_period": attributes.get('MessageRetentionPeriod')
                })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def get_elastic_ips(ec2_client) -> List[Dict[str, Any]]:
    """Get Elastic IPs."""
    try:
        eips = ec2_client.describe_addresses()
        result = []
        for eip in eips['Addresses']:
            result.append({
                "allocation_id": eip.get('AllocationId'),
                "public_ip": eip.get('PublicIp'),
                "domain": eip.get('Domain'),
                "association_id": eip.get('AssociationId'),
                "instance_id": eip.get('InstanceId'),
                "network_interface_id": eip.get('NetworkInterfaceId')
            })
        return result
    except Exception as e:
        return [{"error": str(e)}]

def main():
    """Generate comprehensive infrastructure report."""
    print("=" * 80)
    print("AWS INFRASTRUCTURE DIAGNOSTIC REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.utcnow().isoformat()}Z")
    print(f"Region: {REGION}")
    print(f"Project: {PROJECT_NAME}")
    print(f"Environment: {ENVIRONMENT}")
    print("=" * 80)
    print()
    
    # Initialize clients
    ec2 = boto3.client('ec2', region_name=REGION)
    lambda_client = boto3.client('lambda', region_name=REGION)
    dynamodb = boto3.client('dynamodb', region_name=REGION)
    rds = boto3.client('rds', region_name=REGION)
    sqs = boto3.client('sqs', region_name=REGION)
    
    # Get VPC ID from Lambda functions first
    lambda_functions = get_lambda_functions(lambda_client)
    vpc_id = None
    if lambda_functions and not any('error' in f for f in lambda_functions):
        for func in lambda_functions:
            if func.get('vpc_config') and func['vpc_config'].get('vpc_id'):
                vpc_id = func['vpc_config']['vpc_id']
                break
    
    # If no VPC from Lambda, try to find it
    if not vpc_id:
        try:
            vpcs = ec2.describe_vpcs()
            # Try to find VPC by tags or use first one
            for vpc in vpcs['Vpcs']:
                tags = {tag['Key']: tag['Value'] for tag in vpc.get('Tags', [])}
                if PROJECT_NAME in tags.get('Name', '') or ENVIRONMENT in tags.get('Name', ''):
                    vpc_id = vpc['VpcId']
                    break
            if not vpc_id and vpcs['Vpcs']:
                vpc_id = vpcs['Vpcs'][0]['VpcId']
        except:
            pass
    
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "region": REGION,
        "project": PROJECT_NAME,
        "environment": ENVIRONMENT,
        "vpc_id": vpc_id
    }
    
    # VPC Information
    print("1. VPC CONFIGURATION")
    print("-" * 80)
    if vpc_id:
        vpc_info = get_vpc_info(ec2, vpc_id)
        report["vpc"] = vpc_info
        print(json.dumps(vpc_info, indent=2))
    else:
        print("⚠️  VPC ID not found")
        report["vpc"] = {"error": "VPC ID not found"}
    print()
    
    # Subnets
    print("2. SUBNETS")
    print("-" * 80)
    if vpc_id:
        subnets = get_subnets(ec2, vpc_id)
        report["subnets"] = subnets
        print(json.dumps(subnets, indent=2))
    else:
        print("⚠️  Cannot list subnets - VPC ID unknown")
        report["subnets"] = []
    print()
    
    # Route Tables
    print("3. ROUTE TABLES")
    print("-" * 80)
    if vpc_id:
        route_tables = get_route_tables(ec2, vpc_id)
        report["route_tables"] = route_tables
        print(json.dumps(route_tables, indent=2))
    else:
        print("⚠️  Cannot list route tables - VPC ID unknown")
        report["route_tables"] = []
    print()
    
    # NAT Gateways
    print("4. NAT GATEWAYS")
    print("-" * 80)
    if vpc_id:
        nat_gws = get_nat_gateways(ec2, vpc_id)
        report["nat_gateways"] = nat_gws
        print(json.dumps(nat_gws, indent=2))
    else:
        print("⚠️  Cannot list NAT Gateways - VPC ID unknown")
        report["nat_gateways"] = []
    print()
    
    # Internet Gateways
    print("5. INTERNET GATEWAYS")
    print("-" * 80)
    if vpc_id:
        igws = get_internet_gateways(ec2, vpc_id)
        report["internet_gateways"] = igws
        print(json.dumps(igws, indent=2))
    else:
        print("⚠️  Cannot list Internet Gateways - VPC ID unknown")
        report["internet_gateways"] = []
    print()
    
    # VPC Endpoints
    print("6. VPC ENDPOINTS")
    print("-" * 80)
    if vpc_id:
        endpoints = get_vpc_endpoints(ec2, vpc_id)
        report["vpc_endpoints"] = endpoints
        print(json.dumps(endpoints, indent=2))
    else:
        print("⚠️  Cannot list VPC Endpoints - VPC ID unknown")
        report["vpc_endpoints"] = []
    print()
    
    # Security Groups
    print("7. SECURITY GROUPS")
    print("-" * 80)
    if vpc_id:
        security_groups = get_security_groups(ec2, vpc_id)
        report["security_groups"] = security_groups
        print(json.dumps(security_groups, indent=2))
    else:
        print("⚠️  Cannot list Security Groups - VPC ID unknown")
        report["security_groups"] = []
    print()
    
    # Lambda Functions
    print("8. LAMBDA FUNCTIONS")
    print("-" * 80)
    report["lambda_functions"] = lambda_functions
    print(json.dumps(lambda_functions, indent=2))
    print()
    
    # Lambda ENIs
    print("9. LAMBDA NETWORK INTERFACES (ENIs)")
    print("-" * 80)
    function_names = [f['function_name'] for f in lambda_functions if 'error' not in f]
    if function_names:
        enis = get_lambda_enis(ec2, function_names)
        report["lambda_enis"] = enis
        print(json.dumps(enis, indent=2))
    else:
        print("⚠️  No Lambda functions found")
        report["lambda_enis"] = []
    print()
    
    # DynamoDB Tables
    print("10. DYNAMODB TABLES")
    print("-" * 80)
    dynamodb_tables = get_dynamodb_tables(dynamodb)
    report["dynamodb_tables"] = dynamodb_tables
    print(json.dumps(dynamodb_tables, indent=2))
    print()
    
    # RDS Instances
    print("11. RDS INSTANCES")
    print("-" * 80)
    rds_instances = get_rds_instances(rds)
    report["rds_instances"] = rds_instances
    print(json.dumps(rds_instances, indent=2))
    print()
    
    # SQS Queues
    print("12. SQS QUEUES")
    print("-" * 80)
    sqs_queues = get_sqs_queues(sqs)
    report["sqs_queues"] = sqs_queues
    print(json.dumps(sqs_queues, indent=2))
    print()
    
    # Elastic IPs
    print("13. ELASTIC IPs")
    print("-" * 80)
    eips = get_elastic_ips(ec2)
    report["elastic_ips"] = eips
    print(json.dumps(eips, indent=2))
    print()
    
    # Save full report to JSON file
    output_file = f"infrastructure-report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print("=" * 80)
    print(f"✅ Full report saved to: {output_file}")
    print("=" * 80)
    
    return report

if __name__ == "__main__":
    main()

