env             = "prod"
project         = "ugram"
aws_region      = "us-east-2"
account_id      = "315883835287"
allowed_origins = ["https://d32n58cbhk5j71.cloudfront.net"]
vpc_cidr        = "10.1.0.0/16"
public_subnet_cidrs = [
  "10.1.0.0/24",
  "10.1.1.0/24",
]
private_subnet_cidrs = [
  "10.1.10.0/24",
  "10.1.11.0/24",
]
db_name                                = "ugram"
db_username                            = "ugram"
db_instance_class                      = "db.t4g.micro"
db_allocated_storage                   = 20
db_max_allocated_storage               = 100
db_backup_retention_period             = 0
db_deletion_protection                 = false
db_skip_final_snapshot                 = true
frontend_price_class                   = "PriceClass_100"
frontend_bucket_force_destroy          = false
backend_instance_type                  = "t4g.micro"
backend_image_tag                      = "latest"
backend_healthcheck_path               = "/health"
backend_artifacts_bucket_force_destroy = false
slack_workspace_id                     = "T0AN2JMDT7Y"
infra_slack_channel_id                 = "C0AN2ST3NR4"
backend_env = {
  ALGORITHM                   = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES = "30"
  FRONTEND_URL                = "https://d32n58cbhk5j71.cloudfront.net"
  GOOGLE_AUTH_URL             = "https://accounts.google.com/o/oauth2/v2/auth"
  GOOGLE_TOKEN_URL            = "https://oauth2.googleapis.com/token"
  GOOGLE_CERTS_URL            = "https://www.googleapis.com/oauth2/v3/certs"
  GOOGLE_REDIRECT_URI         = "https://d178t3hbv3f9me.cloudfront.net/auth/google/callback"
  GOOGLE_CLIENT_ID            = "666467504113-mg5p5msto84nchi0sattq32r074feo42.apps.googleusercontent.com"
}
