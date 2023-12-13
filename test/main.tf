provider "aws" {
  region = "us-east-1"
}

resource "aws_ssm_parameter" "test_create" {
  name  = "test_create"
  type  = "SecureString"
  value = "test"
}

resource "aws_ssm_parameter" "test_update" {
  name  = "test_update"
  type  = "SecureString"
  value = "test1"
}

resource "aws_ssm_parameter" "test_replace" {
  name  = "test_replace1"
  type  = "SecureString"
  value = "test"
}

resource "aws_ssm_parameter" "test_delete" {
  name  = "test_delete"
  type  = "SecureString"
  value = "test"
}