# VPC Endpoints for AWS Services
# These allow Lambda functions in the VPC to access AWS services without internet access

# Get VPC ID from subnet
data "aws_vpc" "main" {
  id = data.aws_subnet.main[0].vpc_id
}

# Get route tables for the VPC
data "aws_route_tables" "main" {
  vpc_id = data.aws_vpc.main.id
}

# VPC Endpoint for DynamoDB (Gateway type - no security group needed)
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = data.aws_vpc.main.id
  service_name       = "com.amazonaws.${var.aws_region}.dynamodb"
  vpc_endpoint_type  = "Gateway"
  route_table_ids    = data.aws_route_tables.main.ids

  tags = {
    Name = "${var.project_name}-${var.environment}-dynamodb-endpoint"
  }
}

# VPC Endpoint for SQS
resource "aws_vpc_endpoint" "sqs" {
  vpc_id              = data.aws_vpc.main.id
  service_name         = "com.amazonaws.${var.aws_region}.sqs"
  vpc_endpoint_type    = "Interface"
  subnet_ids           = var.subnet_ids
  security_group_ids   = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled  = true

  tags = {
    Name = "${var.project_name}-${var.environment}-sqs-endpoint"
  }
}

# VPC Endpoint for STS (Security Token Service)
# Required for Lambda functions in VPC to assume IAM roles
resource "aws_vpc_endpoint" "sts" {
  vpc_id              = data.aws_vpc.main.id
  service_name         = "com.amazonaws.${var.aws_region}.sts"
  vpc_endpoint_type    = "Interface"
  subnet_ids           = var.subnet_ids
  security_group_ids   = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled  = true

  tags = {
    Name = "${var.project_name}-${var.environment}-sts-endpoint"
  }
}

# Security Group for VPC Endpoints
resource "aws_security_group" "vpc_endpoint" {
  name        = "${var.project_name}-${var.environment}-vpc-endpoint-sg"
  description = "Security group for VPC endpoints"
  vpc_id      = data.aws_vpc.main.id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]  # Allow from Lambda SG
  }

  # Also allow from VPC CIDR for other resources
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [data.aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-vpc-endpoint-sg"
  }
}

