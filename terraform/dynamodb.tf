# DynamoDB Table for events
resource "aws_dynamodb_table" "events" {
  name           = "${var.dynamodb_table_name}-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST" # On-demand pricing
  hash_key       = "customer_id"
  range_key      = "event_id"

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "event_id"
    type = "S"
  }

  # TTL attribute
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  # Encryption at rest
  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-events"
  }
}

# Outputs
output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.events.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB table ARN"
  value       = aws_dynamodb_table.events.arn
}

