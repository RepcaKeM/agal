# Terraform skeleton: remote state, pinned versions, prevent_destroy on stateful.

terraform {
  required_version = ">= 1.7, < 2.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.40"
    }
  }

  # Remote state in S3 + DynamoDB lock. Never local state for shared infra.
  backend "s3" {
    bucket         = "acme-tfstate-prod"
    key            = "platform/api/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "tfstate-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = "eu-central-1"
  default_tags {
    tags = {
      env       = var.env
      service   = "api"
      managed_by = "terraform"
      owner     = "platform"
    }
  }
}

# Example stateful resource — guarded from accidental destroy.
resource "aws_db_instance" "primary" {
  identifier        = "api-${var.env}"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = "db.t4g.medium"
  allocated_storage = 100
  storage_encrypted = true
  username          = "api"
  manage_master_user_password = true   # rotated by Secrets Manager
  skip_final_snapshot = false
  deletion_protection = true

  lifecycle {
    prevent_destroy = true             # plan will refuse to destroy
  }
}
