# Used to generate a plan with a create, update, replace and destroy for the aggregate test.
# Uses only built-in terraform_data resources with local state, so no cloud credentials are needed.
# The workflow applies with phase=1, then plans with phase=2.

variable "phase" {
  type = number
}

resource "terraform_data" "test_create" {
  count = var.phase == 2 ? 1 : 0
  input = "test"
}

resource "terraform_data" "test_update" {
  input = "phase-${var.phase}"
}

resource "terraform_data" "test_replace" {
  triggers_replace = var.phase
}

resource "terraform_data" "test_destroy" {
  count = var.phase == 1 ? 1 : 0
  input = "test"
}
