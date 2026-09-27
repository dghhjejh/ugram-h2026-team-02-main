variable "env" {
  description = "Deployment environment name"
  type        = string
}

variable "project" {
  description = "Project short name"
  type        = string
}

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
}

variable "account_id" {
  description = "AWS account ID to ensure globally-unique bucket names"
  type        = string
}

variable "allowed_origins" {
  description = "List of origins allowed for S3 CORS (e.g., https://app.example.com, http://localhost:5173)"
  type        = list(string)
  default     = ["http://localhost:5173"]
}

variable "vpc_cidr" {
  description = "CIDR block for the application VPC"
  type        = string
}

variable "public_subnet_cidrs" {
  description = "Two CIDR blocks for public subnets used by internet-facing resources"
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_cidrs) == 2
    error_message = "Exactly two public subnet CIDR blocks are required."
  }
}

variable "private_subnet_cidrs" {
  description = "Two CIDR blocks for private subnets used by RDS"
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Exactly two private subnet CIDR blocks are required."
  }
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
}

variable "db_username" {
  description = "Master username for PostgreSQL"
  type        = string
}

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "16"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
}

variable "db_allocated_storage" {
  description = "Initial storage size for the database in GiB"
  type        = number
}

variable "db_max_allocated_storage" {
  description = "Maximum storage size for autoscaling in GiB"
  type        = number
  default     = 100
}

variable "db_backup_retention_period" {
  description = "Number of days to keep automated backups"
  type        = number
  default     = 0
}

variable "db_deletion_protection" {
  description = "Enable deletion protection on the database"
  type        = bool
  default     = false
}

variable "db_skip_final_snapshot" {
  description = "Skip the final snapshot when destroying the database"
  type        = bool
  default     = true
}

variable "frontend_price_class" {
  description = "CloudFront price class for the frontend distribution"
  type        = string
  default     = "PriceClass_100"
}

variable "frontend_bucket_force_destroy" {
  description = "Allow Terraform to delete the frontend bucket even if it contains files"
  type        = bool
  default     = false
}

variable "backend_solution_stack_name" {
  description = "Elastic Beanstalk Docker solution stack name"
  type        = string
  default     = "64bit Amazon Linux 2023 v4.10.0 running Docker"

}

variable "backend_instance_type" {
  description = "EC2 instance type for the Elastic Beanstalk environment"
  type        = string
  default     = "t4g.small"
}

variable "backend_container_port" {
  description = "Container port exposed by the backend image"
  type        = number
  default     = 8001
}

variable "backend_image_tag" {
  description = "Docker image tag deployed from ECR"
  type        = string
  default     = "latest"
}

variable "release_name" {
  description = "Shared release identifier used for deploy metadata such as Sentry releases"
  type        = string
  default     = null
}

variable "backend_healthcheck_path" {
  description = "HTTP path used by Elastic Beanstalk health checks"
  type        = string
  default     = "/"
}

variable "backend_price_class" {
  description = "CloudFront price class for the backend HTTPS distribution"
  type        = string
  default     = "PriceClass_100"
}

variable "backend_artifacts_bucket_force_destroy" {
  description = "Allow Terraform to delete the Elastic Beanstalk artifacts bucket even if it contains application versions"
  type        = bool
  default     = false
}

variable "backend_s3_upload_prefix" {
  description = "S3 prefix used by the backend for uploaded images"
  type        = string
  default     = "images"
}

variable "backend_s3_presign_ttl" {
  description = "Default presigned URL TTL in seconds for the backend"
  type        = number
  default     = 900
}

variable "backend_max_upload_size_bytes" {
  description = "Maximum upload size in bytes enforced by the backend"
  type        = number
  default     = 10485760
}

variable "backend_oauth_state_cookie_name" {
  description = "Cookie name used to store the Google OAuth state"
  type        = string
  default     = "ugram_oauth_state"
}

variable "backend_oauth_state_ttl_seconds" {
  description = "Lifetime of the Google OAuth state cookie in seconds"
  type        = number
  default     = 600
}

variable "backend_env" {
  description = "Additional backend environment variables injected into Elastic Beanstalk"
  type        = map(string)
  default     = {}
}

variable "backend_secret_key_value" {
  description = "Backend JWT signing secret stored in SSM by Terraform"
  type        = string
  sensitive   = true
}

variable "backend_google_client_secret_value" {
  description = "Google OAuth client secret stored in SSM by Terraform"
  type        = string
  sensitive   = true
}

variable "backend_sentry_dsn_value" {
  description = "Optional backend Sentry DSN stored in SSM by Terraform"
  type        = string
  sensitive   = true
  default     = null
}

variable "enable_monitoring" {
  description = "Enable monitoring resources for the current environment"
  type        = bool
  default     = true
}

variable "enable_slack_notifications" {
  description = "Enable the Amazon Q Developer in chat applications Slack configuration when workspace and channel IDs are provided"
  type        = bool
  default     = true
}

variable "monitoring_log_retention_days" {
  description = "Retention period in days for Elastic Beanstalk logs streamed to CloudWatch Logs"
  type        = number
  default     = 14
}

variable "monitoring_chatbot_logging_level" {
  description = "Logging level for the Amazon Q Developer in chat applications Slack configuration"
  type        = string
  default     = "ERROR"
}

variable "monitoring_chatbot_guardrail_policy_arns" {
  description = "Guardrail policies attached to the Amazon Q Developer in chat applications Slack configuration"
  type        = list(string)
  default     = ["arn:aws:iam::aws:policy/ReadOnlyAccess"]
}

variable "slack_workspace_id" {
  description = "Slack workspace ID authorized in Amazon Q Developer in chat applications"
  type        = string
  default     = null
}

variable "infra_slack_channel_id" {
  description = "Slack channel ID for infrastructure alerts, for example the channel behind #dev-infra-alerts"
  type        = string
  default     = null
}

variable "monitoring_ec2_cpu_utilization_threshold" {
  description = "CPU utilization percentage threshold for the Elastic Beanstalk EC2 instance alarm"
  type        = number
  default     = 80
}

variable "monitoring_rds_cpu_utilization_threshold" {
  description = "CPU utilization percentage threshold for the RDS alarm"
  type        = number
  default     = 80
}

variable "monitoring_rds_free_storage_space_threshold_bytes" {
  description = "Free storage threshold in bytes for the RDS alarm"
  type        = number
  default     = 5368709120
}

variable "monitoring_rds_freeable_memory_threshold_bytes" {
  description = "Freeable memory threshold in bytes for the RDS alarm"
  type        = number
  default     = 268435456
}

variable "monitoring_rds_read_latency_threshold_seconds" {
  description = "Read latency threshold in seconds for the RDS alarm"
  type        = number
  default     = 0.2
}

variable "monitoring_rds_write_latency_threshold_seconds" {
  description = "Write latency threshold in seconds for the RDS alarm"
  type        = number
  default     = 0.2
}

variable "monitoring_cloudfront_5xx_error_rate_threshold" {
  description = "5xx error rate percentage threshold for the CloudFront alarms"
  type        = number
  default     = 1
}
