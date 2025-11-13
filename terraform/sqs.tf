# SQS Queue for events
resource "aws_sqs_queue" "event_queue" {
  name                      = "${var.project_name}-${var.environment}-events"
  message_retention_seconds = 1209600 # 14 days
  visibility_timeout_seconds = 300     # 5 minutes
  receive_wait_time_seconds  = 20      # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.event_dlq.arn
    maxReceiveCount     = 5
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-events"
  }
}

# Dead Letter Queue
resource "aws_sqs_queue" "event_dlq" {
  name                      = "${var.project_name}-${var.environment}-events-dlq"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Name = "${var.project_name}-${var.environment}-events-dlq"
  }
}

# Outputs
output "sqs_event_queue_url" {
  description = "SQS event queue URL"
  value       = aws_sqs_queue.event_queue.url
}

output "sqs_event_queue_arn" {
  description = "SQS event queue ARN"
  value       = aws_sqs_queue.event_queue.arn
}

output "sqs_dlq_url" {
  description = "SQS dead letter queue URL"
  value       = aws_sqs_queue.event_dlq.url
}

output "sqs_dlq_arn" {
  description = "SQS dead letter queue ARN"
  value       = aws_sqs_queue.event_dlq.arn
}

