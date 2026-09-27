bucket         = "ugram-terraform-state"
key            = "prod/terraform.tfstate"
region         = "us-east-2"
dynamodb_table = "ugram-terraform-lock"
encrypt        = true
