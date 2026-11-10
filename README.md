# terraform-pr-summary

A GitHub Action which adds a comment to a GitHub pull request with a summary of Terraform changes

[![.github/workflows/golint.yml](https://github.com/champ-oss/terraform-pr-summary/actions/workflows/golint.yml/badge.svg?branch=main)](https://github.com/champ-oss/terraform-pr-summary/actions/workflows/golint.yml)
[![.github/workflows/release.yml](https://github.com/champ-oss/terraform-pr-summary/actions/workflows/release.yml/badge.svg)](https://github.com/champ-oss/terraform-pr-summary/actions/workflows/release.yml)

## Example

👉 Plan: 1 to add, 2 to change, 1 to destroy.

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

      - uses: hashicorp/setup-terraform@v1.3.2

      - uses: champ-oss/terraform-pr-summary
        if: github.event_name == 'pull_request'
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
```


## Many plans in one comment (matrix)

When a workflow plans many tfvars files in a matrix, posting one comment per plan floods the pull request.
Use `comment: false` in the matrix job, upload each JSON summary, then use `mode: aggregate` in a final job to post a
single comment with a totals table at the top, followed by a collapsed section for each plan with changes. The header
shows the plan identifier and its change counts, expanding it lists the resources created, updated, replaced and
destroyed. Plans with no changes are collapsed into a single line. Set `expected-identifiers` to check the number of plans reported against the number
expected, any missing plans are listed as failed.

```yaml
jobs:
  plan:
    strategy:
      matrix:
        TFVARS: ${{ fromJson(needs.setup.outputs.TFVARS) }}
    steps:
      # ... terraform plan -out=tfplan
      - uses: champ-oss/terraform-pr-summary@main
        with:
          plan-file: tfplan
          identifier: ${{ matrix.TFVARS }}
          comment: false
      - uses: actions/upload-artifact@v4
        with:
          name: tf-summary-${{ strategy.job-index }}
          path: terraform-pr-summary.json

  summary:
    needs: [ setup, plan ]
    if: always() && github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
    steps:
      - uses: actions/download-artifact@v4
        with:
          pattern: tf-summary-*
          path: summaries
      - uses: champ-oss/terraform-pr-summary@main
        with:
          mode: aggregate
          summary-dir: summaries
          expected-identifiers: ${{ needs.setup.outputs.TFVARS }}
```

## Parameters
| Parameter | Required | Description |
| --- | --- | --- |
| token | false | GitHub Token or PAT |
| mode | false | `plan` (default) summarizes one plan file, `aggregate` combines many JSON summaries into one comment |
| working-directory | false | Directory to run the action from (default `.`) |
| plan-file | for `plan` | Terraform plan file |
| identifier | false | Custom identifier for the plan (ex: tfvars name) |
| output-file | false | File to write the markdown summary (default `terraform-pr-summary.txt`) |
| json-file | false | File to write the JSON summary in `plan` mode (default `terraform-pr-summary.json`) |
| comment | false | Post a pull request comment (default `true`) |
| skip-no-changes | false | In `plan` mode, don't post a new comment when there are no changes (default `false`) |
| summary-dir | false | Directory searched recursively for JSON summaries in `aggregate` mode (default `.`) |
| expected-identifiers | false | JSON list of identifiers, any without a summary are reported as failed in `aggregate` mode |

## Outputs
| Output | Description |
| --- | --- |
| has-changes | `true` if any plan has creates, updates, replaces or deletes |


## Contributing

