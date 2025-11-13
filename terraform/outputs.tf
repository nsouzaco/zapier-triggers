# Output all important values
output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "aws_region" {
  description = "AWS region"
  value       = var.aws_region
}

output "project_name" {
  description = "Project name"
  value       = var.project_name
}

output "vpc_id" {
  description = "VPC ID"
  value       = length(var.subnet_ids) > 0 ? data.aws_subnet.main[0].vpc_id : null
}

output "subnet_ids" {
  description = "Subnet IDs for Lambda VPC configuration"
  value       = var.subnet_ids
}

output "rds_security_group_id" {
  description = "RDS Security Group ID"
  value       = aws_security_group.rds.id
}

output "lambda_security_group_id" {
  description = "Lambda Security Group ID"
  value       = aws_security_group.lambda.id
}

