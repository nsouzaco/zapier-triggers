# NAT Gateway for Lambda Internet Access
# Allows Lambda functions in VPC to access the internet for webhook delivery

# Get route table for Lambda subnets
# Find the route table associated with the Lambda subnets
data "aws_route_table" "lambda" {
  count  = length(var.subnet_ids) > 0 ? 1 : 0
  vpc_id = data.aws_subnet.main[0].vpc_id
  
  filter {
    name   = "association.subnet-id"
    values = var.subnet_ids
  }
}

# Elastic IP for NAT Gateway
resource "aws_eip" "nat" {
  count  = length(var.subnet_ids) > 0 ? 1 : 0
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-${var.environment}-nat-eip"
  }

  depends_on = [data.aws_subnet.main]
}

# NAT Gateway in first public subnet
resource "aws_nat_gateway" "main" {
  count         = length(var.subnet_ids) > 0 ? 1 : 0
  allocation_id = aws_eip.nat[0].id
  subnet_id     = var.subnet_ids[0] # Use first subnet (public subnet)

  tags = {
    Name = "${var.project_name}-${var.environment}-nat-gateway"
  }

  depends_on = [aws_eip.nat]
}

# Update route table to route internet traffic through NAT Gateway
# This replaces the direct Internet Gateway route for Lambda subnets
resource "aws_route" "nat_gateway" {
  count                  = length(var.subnet_ids) > 0 ? 1 : 0
  route_table_id         = data.aws_route_table.lambda[0].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.main[0].id

  # Remove the existing Internet Gateway route if it exists
  # Note: Terraform will handle this automatically when applying
}

