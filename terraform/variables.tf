variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "zapier-triggers-api"
}

variable "dynamodb_table_name" {
  description = "DynamoDB table name for events"
  type        = string
  default     = "triggers-api-events"
}

variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "rds_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "event_retention_days" {
  description = "Event retention period in days"
  type        = number
  default     = 90
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for RDS"
  type        = bool
  default     = false
}

variable "subnet_ids" {
  description = "List of subnet IDs for RDS and ElastiCache"
  type        = list(string)
  default     = []
}

variable "allowed_cidr_blocks" {
  description = "List of CIDR blocks allowed to access RDS and Redis"
  type        = list(string)
  default     = ["0.0.0.0/0"] # WARNING: Change this for production!
}

variable "rds_username" {
  description = "RDS master username"
  type        = string
  default     = "triggers_api"
}

variable "rds_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
  default     = ""
}

