# terraform-pr-summary

A GitHub Action which adds a comment to a GitHub pull request with a summary of Terraform changes

[![.github/workflows/golint.yml](https://github.com/champ-oss/terraform-pr-summary/actions/workflows/golint.yml/badge.svg?branch=main)](https://github.com/champ-oss/terraform-pr-summary/actions/workflows/golint.yml)
[![.github/workflows/release.yml](https://github.com/champ-oss/terraform-pr-summary/actions/workflows/release.yml/badge.svg)](https://github.com/champ-oss/terraform-pr-summary/actions/workflows/release.yml)

## Example

👉 Plan: 3 to add, 2 to change, 10 to destroy.

🛠️ Created:  
random_password.foo

🔀 Updated:  
module.this.module.mysql.aws_db_instance.this

♻️ Replaced:  
module.this.module.app.aws_ecs_task_definition.this  

❌ Deleted:  
module.this.module.ui.aws_route53_record.this

## Example Usage

```yaml
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - uses: hashicorp/setup-terraform@v1.3.2
        with:
          terraform_version: 1.1.4
          terraform_wrapper: false

      - uses: champ-oss/terraform-pr-summary
        if: github.event_name == 'pull_request'
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```


## Parameters
| Parameter | Required | Description |
| --- | --- | --- |
| token | false | GitHub Token or PAT |


## Contributing

