output "images_bucket_name" {
  description = "S3 bucket name for images"
  value       = aws_s3_bucket.images.bucket
}

output "vpc_id" {
  description = "VPC ID for the application network"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs reserved for internet-facing resources"
  value       = [for subnet in aws_subnet.public : subnet.id]
}

output "private_subnet_ids" {
  description = "Private subnet IDs reserved for data services"
  value       = [for subnet in aws_subnet.private : subnet.id]
}

output "backend_security_group_id" {
  description = "Security group ID reserved for backend compute resources"
  value       = aws_security_group.backend.id
}

output "database_security_group_id" {
  description = "Security group ID protecting the PostgreSQL instance"
  value       = aws_security_group.database.id
}

output "rds_endpoint" {
  description = "PostgreSQL endpoint hostname"
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "PostgreSQL endpoint port"
  value       = aws_db_instance.main.port
}

output "database_url_ssm_parameter_name" {
  description = "SSM parameter name containing the backend DATABASE_URL"
  value       = aws_ssm_parameter.database_url.name
}

output "frontend_bucket_name" {
  description = "S3 bucket name that stores the frontend build artifacts"
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_cloudfront_distribution_id" {
  description = "CloudFront distribution ID serving the frontend"
  value       = aws_cloudfront_distribution.frontend.id
}

output "frontend_url" {
  description = "Public CloudFront URL for the frontend"
  value       = "https://${aws_cloudfront_distribution.frontend.domain_name}"
}

output "backend_ecr_repository_url" {
  description = "ECR repository URL for the backend image"
  value       = aws_ecr_repository.backend.repository_url
}

output "backend_artifacts_bucket_name" {
  description = "S3 bucket used to store Elastic Beanstalk application versions"
  value       = aws_s3_bucket.backend_artifacts.bucket
}

output "backend_application_name" {
  description = "Elastic Beanstalk application name for the backend"
  value       = aws_elastic_beanstalk_application.backend.name
}

output "backend_environment_name" {
  description = "Elastic Beanstalk environment name for the backend"
  value       = aws_elastic_beanstalk_environment.backend.name
}

output "backend_url" {
  description = "Public Elastic Beanstalk URL for the backend"
  value       = "http://${aws_elastic_beanstalk_environment.backend.cname}"
}

output "backend_cloudfront_distribution_id" {
  description = "CloudFront distribution ID serving the backend over HTTPS"
  value       = aws_cloudfront_distribution.backend.id
}

output "backend_https_url" {
  description = "Public CloudFront HTTPS URL for the backend"
  value       = "https://${aws_cloudfront_distribution.backend.domain_name}"
}

output "monitoring_alerts_topic_arn" {
  description = "SNS topic ARN used for CloudWatch monitoring alerts when monitoring is enabled"
  value       = try(aws_sns_topic.monitoring_alerts[0].arn, null)
}

output "monitoring_dashboard_name" {
  description = "CloudWatch dashboard name for the environment monitoring view when monitoring is enabled"
  value       = try(aws_cloudwatch_dashboard.monitoring[0].dashboard_name, null)
}

output "infra_slack_chatbot_configuration_arn" {
  description = "Amazon Q Developer in chat applications Slack configuration ARN for infra alerts when Slack is enabled"
  value       = try(aws_chatbot_slack_channel_configuration.infra_alerts[0].chat_configuration_arn, null)
}
