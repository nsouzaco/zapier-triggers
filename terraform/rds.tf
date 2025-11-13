# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name = "${var.project_name}-${var.environment}-subnet-group"
  }
}

# RDS Security Group
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for RDS PostgreSQL"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }
}

# RDS Parameter Group
resource "aws_db_parameter_group" "postgres" {
  name   = "${var.project_name}-${var.environment}-postgres"
  family = "postgres15"

  tags = {
    Name = "${var.project_name}-${var.environment}-postgres"
  }
}

# RDS Instance
resource "aws_db_instance" "postgres" {
  identifier             = "${var.project_name}-${var.environment}-postgres"
  engine                 = "postgres"
  engine_version         = "15.14"
  instance_class         = var.rds_instance_class
  allocated_storage      = var.rds_allocated_storage
  storage_type           = "gp3"
  storage_encrypted      = true

  db_name  = "triggers_api"
  username = var.rds_username
  password = var.rds_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name    = aws_db_parameter_group.postgres.name
  publicly_accessible     = true  # Allow public access (temporary workaround for NAT Gateway)

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  skip_final_snapshot       = var.environment != "prod"
  final_snapshot_identifier = var.environment == "prod" ? "${var.project_name}-${var.environment}-final-snapshot" : null
  deletion_protection      = var.enable_deletion_protection

  tags = {
    Name = "${var.project_name}-${var.environment}-postgres"
  }
}

# Outputs
output "rds_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "rds_database_url" {
  description = "RDS database URL"
  value       = "postgresql://${var.rds_username}:${var.rds_password}@${aws_db_instance.postgres.endpoint}/${aws_db_instance.postgres.db_name}"
  sensitive   = true
}

