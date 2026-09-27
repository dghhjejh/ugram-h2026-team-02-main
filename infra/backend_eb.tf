locals {
  backend_release = coalesce(var.release_name, var.backend_image_tag)
  backend_default_env = {
    APP_ENV                 = var.env
    DATABASE_MODE           = "rds"
    RDS_DATABASE_URL        = aws_ssm_parameter.database_url.value
    S3_BUCKET               = aws_s3_bucket.images.bucket
    S3_REGION               = var.aws_region
    S3_UPLOAD_PREFIX        = var.backend_s3_upload_prefix
    S3_PRESIGN_TTL          = tostring(var.backend_s3_presign_ttl)
    OAUTH_STATE_COOKIE_NAME = var.backend_oauth_state_cookie_name
    OAUTH_STATE_TTL_SECONDS = tostring(var.backend_oauth_state_ttl_seconds)
    MAX_UPLOAD_SIZE_BYTES   = tostring(var.backend_max_upload_size_bytes)
    SENTRY_ENVIRONMENT      = var.env
    SENTRY_RELEASE          = local.backend_release
    AWS_SDK_LOAD_CONFIG     = "false"
  }
  backend_secret_env = merge(
    {
      DATABASE_URL         = aws_ssm_parameter.database_url.arn
      SECRET_KEY           = aws_ssm_parameter.backend_secret_key.arn
      GOOGLE_CLIENT_SECRET = aws_ssm_parameter.backend_google_client_secret.arn
    },
    var.backend_sentry_dsn_value != null ? { SENTRY_DSN = aws_ssm_parameter.backend_sentry_dsn[0].arn } : {},
  )
  backend_ssm_parameter_arns = concat(
    [
      aws_ssm_parameter.database_url.arn,
      aws_ssm_parameter.backend_secret_key.arn,
      aws_ssm_parameter.backend_google_client_secret.arn,
    ],
    var.backend_sentry_dsn_value != null ? [aws_ssm_parameter.backend_sentry_dsn[0].arn] : [],
  )
  backend_env = merge(local.backend_default_env, var.backend_env)
  backend_dockerrun_content = jsonencode({
    AWSEBDockerrunVersion = "1"
    Image = {
      Name   = "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"
      Update = "true"
    }
    Ports = [
      {
        ContainerPort = tostring(var.backend_container_port)
      }
    ]
  })
  backend_application_version = "${var.project}-${var.env}-${substr(md5("${local.backend_dockerrun_content}:${data.aws_ecr_image.backend.image_digest}"), 0, 12)}"
}

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project}-backend-${var.env}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

data "aws_ecr_image" "backend" {
  repository_name = aws_ecr_repository.backend.name
  image_tag       = var.backend_image_tag
}

resource "aws_s3_bucket" "backend_artifacts" {
  bucket        = "${var.project}-eb-artifacts-${var.env}-${var.account_id}"
  force_destroy = var.backend_artifacts_bucket_force_destroy
}

resource "aws_s3_bucket_public_access_block" "backend_artifacts" {
  bucket = aws_s3_bucket.backend_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backend_artifacts" {
  bucket = aws_s3_bucket.backend_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_ssm_parameter" "backend_secret_key" {
  name  = "/${var.project}/${var.env}/backend/SECRET_KEY"
  type  = "SecureString"
  value = var.backend_secret_key_value
}

resource "aws_ssm_parameter" "backend_google_client_secret" {
  name  = "/${var.project}/${var.env}/backend/GOOGLE_CLIENT_SECRET"
  type  = "SecureString"
  value = var.backend_google_client_secret_value
}

resource "aws_ssm_parameter" "backend_sentry_dsn" {
  count = var.backend_sentry_dsn_value != null ? 1 : 0

  name  = "/${var.project}/${var.env}/backend/SENTRY_DSN"
  type  = "SecureString"
  value = var.backend_sentry_dsn_value
}

data "aws_iam_policy_document" "eb_service_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["elasticbeanstalk.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eb_service" {
  name               = "${var.project}-${var.env}-eb-service-role"
  assume_role_policy = data.aws_iam_policy_document.eb_service_assume_role.json
}

resource "aws_iam_role_policy_attachment" "eb_service_health" {
  role       = aws_iam_role.eb_service.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkEnhancedHealth"
}

resource "aws_iam_role_policy_attachment" "eb_service_managed_updates" {
  role       = aws_iam_role.eb_service.name
  policy_arn = "arn:aws:iam::aws:policy/AWSElasticBeanstalkManagedUpdatesCustomerRolePolicy"
}

data "aws_iam_policy_document" "eb_ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "eb_ec2" {
  name               = "${var.project}-${var.env}-eb-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.eb_ec2_assume_role.json
}

resource "aws_iam_role_policy_attachment" "eb_ec2_web_tier" {
  role       = aws_iam_role.eb_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier"
}

resource "aws_iam_role_policy_attachment" "eb_ec2_ssm" {
  role       = aws_iam_role.eb_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

data "aws_iam_policy_document" "eb_ec2_inline" {
  statement {
    sid = "AllowEcrPull"

    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetAuthorizationToken",
      "ecr:GetDownloadUrlForLayer",
    ]

    resources = ["*"]
  }

  statement {
    sid = "AllowImageBucketAccess"

    actions = [
      "s3:GetBucketLocation",
      "s3:ListBucket",
    ]

    resources = [aws_s3_bucket.images.arn]
  }

  statement {
    sid = "AllowImageObjectAccess"

    actions = [
      "s3:DeleteObject",
      "s3:GetObject",
      "s3:PutObject",
    ]

    resources = ["${aws_s3_bucket.images.arn}/*"]
  }

  statement {
    sid = "AllowSsmReads"

    actions = [
      "ssm:GetParameter",
      "ssm:GetParameters",
    ]

    resources = local.backend_ssm_parameter_arns
  }

}

resource "aws_iam_role_policy" "eb_ec2_inline" {
  name   = "${var.project}-${var.env}-eb-ec2-inline"
  role   = aws_iam_role.eb_ec2.id
  policy = data.aws_iam_policy_document.eb_ec2_inline.json
}

resource "aws_iam_instance_profile" "eb_ec2" {
  name = "${var.project}-${var.env}-eb-ec2-profile"
  role = aws_iam_role.eb_ec2.name
}

resource "aws_s3_object" "backend_dockerrun" {
  bucket       = aws_s3_bucket.backend_artifacts.id
  key          = "beanstalk/${local.backend_application_version}/Dockerrun.aws.json"
  content      = local.backend_dockerrun_content
  content_type = "application/json"
}

resource "aws_elastic_beanstalk_application" "backend" {
  name        = "${var.project}-backend-${var.env}"
  description = "Backend API application for ${var.project} ${var.env}"
}

resource "aws_elastic_beanstalk_application_version" "backend" {
  name        = local.backend_application_version
  application = aws_elastic_beanstalk_application.backend.name
  bucket      = aws_s3_bucket.backend_artifacts.id
  key         = aws_s3_object.backend_dockerrun.key
  description = "ECR-backed Docker deployment for ${var.backend_image_tag}"
}

resource "aws_elastic_beanstalk_environment" "backend" {
  name                = "${var.project}-backend-${var.env}"
  application         = aws_elastic_beanstalk_application.backend.name
  solution_stack_name = var.backend_solution_stack_name
  version_label       = aws_elastic_beanstalk_application_version.backend.name

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "IamInstanceProfile"
    value     = aws_iam_instance_profile.eb_ec2.name
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "InstanceType"
    value     = var.backend_instance_type
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "SecurityGroups"
    value     = aws_security_group.backend.id
  }

  setting {
    namespace = "aws:ec2:vpc"
    name      = "VPCId"
    value     = aws_vpc.main.id
  }

  setting {
    namespace = "aws:ec2:vpc"
    name      = "Subnets"
    value     = join(",", [for subnet in aws_subnet.public : subnet.id])
  }

  setting {
    namespace = "aws:ec2:vpc"
    name      = "AssociatePublicIpAddress"
    value     = "true"
  }

  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "EnvironmentType"
    value     = "SingleInstance"
  }

  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "ServiceRole"
    value     = aws_iam_role.eb_service.name
  }

  setting {
    namespace = "aws:elasticbeanstalk:healthreporting:system"
    name      = "SystemType"
    value     = "enhanced"
  }

  setting {
    namespace = "aws:elasticbeanstalk:healthreporting:system"
    name      = "ConfigDocument"
    value = jsonencode({
      Version = 1
      CloudWatchMetrics = {
        Environment = {
          ApplicationRequests4xx = 60
          ApplicationRequests5xx = 60
        }
      }
    })
  }

  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "StreamLogs"
    value     = "true"
  }

  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "DeleteOnTerminate"
    value     = "false"
  }

  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs"
    name      = "RetentionInDays"
    value     = tostring(var.monitoring_log_retention_days)
  }

  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs:health"
    name      = "HealthStreamingEnabled"
    value     = "true"
  }

  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs:health"
    name      = "DeleteOnTerminate"
    value     = "false"
  }

  setting {
    namespace = "aws:elasticbeanstalk:cloudwatch:logs:health"
    name      = "RetentionInDays"
    value     = tostring(var.monitoring_log_retention_days)
  }

  setting {
    namespace = "aws:elasticbeanstalk:application"
    name      = "Application Healthcheck URL"
    value     = var.backend_healthcheck_path
  }

  dynamic "setting" {
    for_each = local.backend_env

    content {
      namespace = "aws:elasticbeanstalk:application:environment"
      name      = setting.key
      value     = setting.value
    }
  }

  dynamic "setting" {
    for_each = local.backend_secret_env

    content {
      namespace = "aws:elasticbeanstalk:application:environmentsecrets"
      name      = setting.key
      value     = setting.value
    }
  }

}
