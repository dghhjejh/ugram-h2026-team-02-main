locals {
  db_password_parameter_name  = "/${var.project}/${var.env}/database/password"
  database_url_parameter_name = "/${var.project}/${var.env}/backend/DATABASE_URL"
}

resource "aws_db_subnet_group" "main" {
  name       = "${var.project}-${var.env}-db-subnets"
  subnet_ids = [for subnet in aws_subnet.private : subnet.id]
}

resource "random_password" "database" {
  length  = 32
  special = false
}

resource "aws_db_instance" "main" {
  identifier                   = "${var.project}-${var.env}-postgres"
  engine                       = "postgres"
  engine_version               = var.db_engine_version
  instance_class               = var.db_instance_class
  allocated_storage            = var.db_allocated_storage
  max_allocated_storage        = var.db_max_allocated_storage
  db_name                      = var.db_name
  username                     = var.db_username
  password                     = random_password.database.result
  db_subnet_group_name         = aws_db_subnet_group.main.name
  vpc_security_group_ids       = [aws_security_group.database.id]
  publicly_accessible          = false
  backup_retention_period      = var.db_backup_retention_period
  deletion_protection          = var.db_deletion_protection
  skip_final_snapshot          = var.db_skip_final_snapshot
  storage_encrypted            = true
  auto_minor_version_upgrade   = true
  apply_immediately            = true
  copy_tags_to_snapshot        = true
  multi_az                     = false
  performance_insights_enabled = false
}

resource "aws_ssm_parameter" "database_password" {
  name  = local.db_password_parameter_name
  type  = "SecureString"
  value = random_password.database.result
}

resource "aws_ssm_parameter" "database_url" {
  name  = local.database_url_parameter_name
  type  = "SecureString"
  value = "postgresql://${var.db_username}:${urlencode(random_password.database.result)}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${var.db_name}"
}
