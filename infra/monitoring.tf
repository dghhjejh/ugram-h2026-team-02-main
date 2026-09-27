locals {
  enable_monitoring_resources        = var.enable_monitoring
  enable_slack_notifications_for_env = local.enable_monitoring_resources && var.enable_slack_notifications && var.slack_workspace_id != null && var.infra_slack_channel_id != null

  monitoring_notification_topic_arns = local.enable_monitoring_resources ? [aws_sns_topic.monitoring_alerts[0].arn] : []
  backend_instance_ids               = try(data.aws_instances.backend[0].ids, [])
  backend_instance_id                = length(local.backend_instance_ids) > 0 ? local.backend_instance_ids[0] : null

  backend_health_log_group_name = "/aws/elasticbeanstalk/${aws_elastic_beanstalk_environment.backend.name}/health.log"
  backend_application_log_group_names = [
    "/aws/elasticbeanstalk/${aws_elastic_beanstalk_environment.backend.name}/var/log/eb-engine.log",
    "/aws/elasticbeanstalk/${aws_elastic_beanstalk_environment.backend.name}/var/log/web.stdout.log",
    "/aws/elasticbeanstalk/${aws_elastic_beanstalk_environment.backend.name}/var/log/web.stderr.log",
    "/aws/elasticbeanstalk/${aws_elastic_beanstalk_environment.backend.name}/var/log/nginx/access.log",
    "/aws/elasticbeanstalk/${aws_elastic_beanstalk_environment.backend.name}/var/log/nginx/error.log",
  ]

  monitoring_dashboard_widgets = concat(
    [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Elastic Beanstalk Health"
          region  = var.aws_region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/ElasticBeanstalk", "EnvironmentHealth", "EnvironmentName", aws_elastic_beanstalk_environment.backend.name],
            [".", "ApplicationRequests5xx", ".", "."],
            [".", "ApplicationRequests4xx", ".", "."],
          ]
        }
      }
    ],
    local.backend_instance_id != null ? [
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title   = "Backend EC2 Runtime"
          region  = var.aws_region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/EC2", "CPUUtilization", "InstanceId", local.backend_instance_id],
            [".", "StatusCheckFailed", ".", "."],
          ]
        }
      }
    ] : [],
    [
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "RDS Health"
          region  = var.aws_region
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/RDS", "CPUUtilization", "DBInstanceIdentifier", aws_db_instance.main.id],
            [".", "FreeStorageSpace", ".", "."],
            [".", "FreeableMemory", ".", "."],
            [".", "DatabaseConnections", ".", "."],
            [".", "ReadLatency", ".", "."],
            [".", "WriteLatency", ".", "."],
          ]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title   = "Frontend CloudFront"
          region  = "us-east-1"
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/CloudFront", "5xxErrorRate", "DistributionId", aws_cloudfront_distribution.frontend.id, "Region", "Global"],
            [".", "4xxErrorRate", ".", ".", ".", "."],
            [".", "OriginLatency", ".", ".", ".", "."],
          ]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 12
        width  = 12
        height = 6
        properties = {
          title   = "Backend CloudFront"
          region  = "us-east-1"
          view    = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/CloudFront", "5xxErrorRate", "DistributionId", aws_cloudfront_distribution.backend.id, "Region", "Global"],
            [".", "4xxErrorRate", ".", ".", ".", "."],
            [".", "OriginLatency", ".", ".", ".", "."],
          ]
        }
      },
    ],
  )
}

data "aws_instances" "backend" {
  count = local.enable_monitoring_resources ? 1 : 0

  instance_tags = {
    "elasticbeanstalk:environment-name" = aws_elastic_beanstalk_environment.backend.name
  }

  instance_state_names = ["running"]

  depends_on = [aws_elastic_beanstalk_environment.backend]
}

data "aws_iam_policy_document" "monitoring_chatbot_assume_role" {
  count = local.enable_slack_notifications_for_env ? 1 : 0

  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["chatbot.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "monitoring_chatbot" {
  count = local.enable_slack_notifications_for_env ? 1 : 0

  name               = "${var.project}-${var.env}-chatbot-slack-role"
  assume_role_policy = data.aws_iam_policy_document.monitoring_chatbot_assume_role[0].json
}

resource "aws_iam_role_policy_attachment" "monitoring_chatbot_guardrails" {
  for_each = local.enable_slack_notifications_for_env ? toset(var.monitoring_chatbot_guardrail_policy_arns) : toset([])

  role       = aws_iam_role.monitoring_chatbot[0].name
  policy_arn = each.value
}

resource "aws_sns_topic" "monitoring_alerts" {
  count = local.enable_monitoring_resources ? 1 : 0

  name = "${var.project}-${var.env}-monitoring-alerts"
}

resource "aws_chatbot_slack_channel_configuration" "infra_alerts" {
  count = local.enable_slack_notifications_for_env ? 1 : 0

  configuration_name          = "${var.project}-${var.env}-infra-alerts"
  iam_role_arn                = aws_iam_role.monitoring_chatbot[0].arn
  slack_channel_id            = var.infra_slack_channel_id
  slack_team_id               = var.slack_workspace_id
  sns_topic_arns              = [aws_sns_topic.monitoring_alerts[0].arn]
  guardrail_policy_arns       = var.monitoring_chatbot_guardrail_policy_arns
  logging_level               = var.monitoring_chatbot_logging_level
  user_authorization_required = false
}

resource "aws_cloudwatch_query_definition" "backend_errors" {
  count = local.enable_monitoring_resources ? 1 : 0

  name            = "${var.project}-${var.env}-backend-errors"
  log_group_names = local.backend_application_log_group_names
  query_string    = <<-EOT
    fields @timestamp, @logStream, @message
    | filter @message like /ERROR|Error|Exception|Traceback/
    | sort @timestamp desc
    | limit 50
  EOT
}

resource "aws_cloudwatch_query_definition" "backend_health" {
  count = local.enable_monitoring_resources ? 1 : 0

  name            = "${var.project}-${var.env}-backend-health-stream"
  log_group_names = [local.backend_health_log_group_name]
  query_string    = <<-EOT
    fields @timestamp, @message
    | sort @timestamp desc
    | limit 50
  EOT
}

resource "aws_cloudwatch_dashboard" "monitoring" {
  count = local.enable_monitoring_resources ? 1 : 0

  dashboard_name = "${var.project}-${var.env}-monitoring"
  dashboard_body = jsonencode({
    widgets = local.monitoring_dashboard_widgets
  })
}

resource "aws_cloudwatch_metric_alarm" "beanstalk_environment_health" {
  count = local.enable_monitoring_resources ? 1 : 0

  alarm_name          = "${var.project}-${var.env}-beanstalk-environment-health"
  alarm_description   = "Elastic Beanstalk environment health degraded or worse"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 5
  metric_name         = "EnvironmentHealth"
  namespace           = "AWS/ElasticBeanstalk"
  period              = 60
  statistic           = "Average"
  threshold           = 15
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.monitoring_notification_topic_arns
  ok_actions          = local.monitoring_notification_topic_arns

  dimensions = {
    EnvironmentName = aws_elastic_beanstalk_environment.backend.name
  }
}

resource "aws_cloudwatch_metric_alarm" "backend_instance_status" {
  count = local.enable_monitoring_resources ? 1 : 0

  alarm_name          = "${var.project}-${var.env}-backend-instance-status"
  alarm_description   = "Elastic Beanstalk EC2 instance status checks are failing"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  treat_missing_data  = "breaching"
  alarm_actions       = local.monitoring_notification_topic_arns
  ok_actions          = local.monitoring_notification_topic_arns

  dimensions = {
    InstanceId = local.backend_instance_id
  }
}

resource "aws_cloudwatch_metric_alarm" "backend_instance_cpu" {
  count = local.enable_monitoring_resources ? 1 : 0

  alarm_name          = "${var.project}-${var.env}-backend-instance-cpu"
  alarm_description   = "Elastic Beanstalk EC2 instance CPU is elevated"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Average"
  threshold           = var.monitoring_ec2_cpu_utilization_threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.monitoring_notification_topic_arns
  ok_actions          = local.monitoring_notification_topic_arns

  dimensions = {
    InstanceId = local.backend_instance_id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  count = local.enable_monitoring_resources ? 1 : 0

  alarm_name          = "${var.project}-${var.env}-rds-cpu"
  alarm_description   = "RDS CPU is elevated"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = var.monitoring_rds_cpu_utilization_threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.monitoring_notification_topic_arns
  ok_actions          = local.monitoring_notification_topic_arns

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_free_storage" {
  count = local.enable_monitoring_resources ? 1 : 0

  alarm_name          = "${var.project}-${var.env}-rds-free-storage"
  alarm_description   = "RDS free storage is low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 5
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = var.monitoring_rds_free_storage_space_threshold_bytes
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.monitoring_notification_topic_arns
  ok_actions          = local.monitoring_notification_topic_arns

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_freeable_memory" {
  count = local.enable_monitoring_resources ? 1 : 0

  alarm_name          = "${var.project}-${var.env}-rds-freeable-memory"
  alarm_description   = "RDS freeable memory is low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 5
  metric_name         = "FreeableMemory"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = var.monitoring_rds_freeable_memory_threshold_bytes
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.monitoring_notification_topic_arns
  ok_actions          = local.monitoring_notification_topic_arns

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_read_latency" {
  count = local.enable_monitoring_resources ? 1 : 0

  alarm_name          = "${var.project}-${var.env}-rds-read-latency"
  alarm_description   = "RDS read latency is elevated"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "ReadLatency"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = var.monitoring_rds_read_latency_threshold_seconds
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.monitoring_notification_topic_arns
  ok_actions          = local.monitoring_notification_topic_arns

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "rds_write_latency" {
  count = local.enable_monitoring_resources ? 1 : 0

  alarm_name          = "${var.project}-${var.env}-rds-write-latency"
  alarm_description   = "RDS write latency is elevated"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 5
  metric_name         = "WriteLatency"
  namespace           = "AWS/RDS"
  period              = 60
  statistic           = "Average"
  threshold           = var.monitoring_rds_write_latency_threshold_seconds
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.monitoring_notification_topic_arns
  ok_actions          = local.monitoring_notification_topic_arns

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "frontend_cloudfront_5xx" {
  count = local.enable_monitoring_resources ? 1 : 0

  alarm_name          = "${var.project}-${var.env}-frontend-cloudfront-5xx"
  alarm_description   = "Frontend CloudFront 5xx error rate is elevated"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "5xxErrorRate"
  namespace           = "AWS/CloudFront"
  period              = 300
  statistic           = "Average"
  threshold           = var.monitoring_cloudfront_5xx_error_rate_threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.monitoring_notification_topic_arns
  ok_actions          = local.monitoring_notification_topic_arns

  dimensions = {
    DistributionId = aws_cloudfront_distribution.frontend.id
    Region         = "Global"
  }
}

resource "aws_cloudwatch_metric_alarm" "backend_cloudfront_5xx" {
  count = local.enable_monitoring_resources ? 1 : 0

  alarm_name          = "${var.project}-${var.env}-backend-cloudfront-5xx"
  alarm_description   = "Backend CloudFront 5xx error rate is elevated"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "5xxErrorRate"
  namespace           = "AWS/CloudFront"
  period              = 300
  statistic           = "Average"
  threshold           = var.monitoring_cloudfront_5xx_error_rate_threshold
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.monitoring_notification_topic_arns
  ok_actions          = local.monitoring_notification_topic_arns

  dimensions = {
    DistributionId = aws_cloudfront_distribution.backend.id
    Region         = "Global"
  }
}
