import glob
import json
import os
import subprocess
from json import JSONDecodeError
from typing import List, Optional

AGGREGATE_MARKER = '<!-- terraform-pr-summary:aggregate -->'
MAX_COMMENT_LENGTH = 60000  # GitHub limit is 65536


def get_terraform_plan_json(plan_file_path: str) -> str:
    """
    Get the Terraform plan as a JSON string

    :param plan_file_path: local path for Terraform plan file
    :return: Terraform plan as JSON string
    """
    command = ['terraform', 'show', '-json', plan_file_path]
    print('running command: ' + ' '.join(command))
    return subprocess.run(command, stdout=subprocess.PIPE).stdout.decode('utf-8')


def parse_resource_changes(plan_json: str) -> List[dict]:
    """
    Parse the JSON Terraform Plan and return the list of resource changes

    :param plan_json: Terraform plan as JSON string
    :return: list of Terraform resource changes
    """
    try:
        plan = json.loads(plan_json)
        return plan.get('resource_changes', [])
    except JSONDecodeError:
        print('Failed to parse Terraform plan JSON, did you run terraform init?')
        raise Exception


def get_create_changes(resource_changes: List[dict]) -> List[str]:
    """
    Parse the Terraform plan resource changes and return a list of resource being created
    https://developer.hashicorp.com/terraform/internals/json-format#change-representation

    :param resource_changes: list of Terraform resource changes
    :return: list of Terraform resources being created
    """
    return [resource['address'] for resource in resource_changes
            if resource['change']['actions'] == ['create']]


def get_update_changes(resource_changes: List[dict]) -> List[str]:
    """
    Parse the Terraform plan resource changes and return a list of resource being updated
    https://developer.hashicorp.com/terraform/internals/json-format#change-representation

    :param resource_changes: list of Terraform resource changes
    :return: list of Terraform resources being updated
    """
    return [resource['address'] for resource in resource_changes
            if resource['change']['actions'] == ['update']]


def get_delete_changes(resource_changes: List[dict]) -> List[str]:
    """
    Parse the Terraform plan resource changes and return a list of resource being deleted
    https://developer.hashicorp.com/terraform/internals/json-format#change-representation

    :param resource_changes: list of Terraform resource changes
    :return: list of Terraform resources being deleted
    """
    return [resource['address'] for resource in resource_changes
            if resource['change']['actions'] == ['delete']]


def get_replace_changes(resource_changes: List[dict]) -> List[str]:
    """
    Parse the Terraform plan resource changes and return a list of resource being replaced
    https://developer.hashicorp.com/terraform/internals/json-format#change-representation

    :param resource_changes: list of Terraform resource changes
    :return: list of Terraform resources being replaced
    """
    return [resource['address'] for resource in resource_changes
            if resource['change']['actions'] == ['delete', 'create'] or
            resource['change']['actions'] == ['create', 'delete']]


def append_to_output(output: str, items: List[str], description: str) -> str:
    """
    Append a list of Terraform resources and a description to the output string

    :param output: overall terraform plan output string
    :param items: list of Terraform resources
    :param description: description of resources (ex: created, deleted, etc)
    :return: appended output string
    """
    if not items:
        return output
    output += f'\n**{description}**:\n'
    for item in items:
        output += f'{item}\n'
    return output


def build_output_header(custom_identifier: str) -> str:
    """
    Set a header for the terraform plan output string

    :param custom_identifier: custom string to add to the header (ex: tfvars filename)
    :return: appended output string
    """
    if custom_identifier:
        print(f'using custom identifier: {custom_identifier}')
        return f'**Terraform Plan ({custom_identifier})**\n\n'
    return '**Terraform Plan**\n\n'


def append_changes_to_output(output: str, resource_changes: List[dict]) -> str:
    """
    Get the list of created, updated, replaced, deleted resources and append to the output summary

    :param output: overall terraform plan output string
    :param resource_changes: list of Terraform resource changes
    :return: appended output string
    """
    create = get_create_changes(resource_changes)
    update = get_update_changes(resource_changes)
    replace = get_replace_changes(resource_changes)
    delete = get_delete_changes(resource_changes)

    return append_change_lists(output, create, update, replace, delete)


def append_change_lists(output: str, create: List[str], update: List[str], replace: List[str],
                        delete: List[str]) -> str:
    """
    Append the change counts and the lists of created, updated, replaced, deleted resources to the output summary

    :param output: overall terraform plan output string
    :param create: resources being created
    :param update: resources being updated
    :param replace: resources being replaced
    :param delete: resources being deleted
    :return: appended output string
    """
    output += format_change_counts(create, update, replace, delete)
    output = append_to_output(output, create, '🛠️ Created')
    output = append_to_output(output, update, '🔀 Updated')
    output = append_to_output(output, replace, '♻️ Replaced')
    output = append_to_output(output, delete, '❌ Deleted')
    return output


def format_change_counts(create: List[str], update: List[str], replace: List[str], delete: List[str]) -> str:
    """
    :return: change counts line (ex: "👉 1 to create, 0 to update, 0 to replace, 0 to destroy")
    """
    return f'👉 {len(create)} to create, {len(update)} to update, ' \
           f'{len(replace)} to replace, {len(delete)} to destroy\n'


def write_output(output: str, file_name: str) -> None:
    """
    Write the output string to the given file name

    :param output: overall terraform plan output string
    :param file_name: local file name to write
    :return: None
    """
    print(f'writing output to file: {file_name}')
    with open(file_name, 'w') as f:
        f.write(output)


def build_summary(identifier: str, resource_changes: List[dict]) -> dict:
    """
    Build a machine-readable summary of the plan, used for aggregating many plans into one comment

    :param identifier: custom identifier (ex: tfvars name)
    :param resource_changes: list of Terraform resource changes
    :return: summary dictionary
    """
    return {
        'identifier': identifier or '',
        'create': get_create_changes(resource_changes),
        'update': get_update_changes(resource_changes),
        'replace': get_replace_changes(resource_changes),
        'delete': get_delete_changes(resource_changes),
    }


def has_changes(summary: dict) -> bool:
    """
    :param summary: summary dictionary from build_summary
    :return: True if the plan has any create, update, replace or delete
    """
    return any(summary.get(key) for key in ('create', 'update', 'replace', 'delete'))


def write_github_output(name: str, value: str) -> None:
    """
    Write a step output when running in GitHub Actions

    :param name: output name
    :param value: output value
    :return: None
    """
    github_output = os.getenv('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f'{name}={value}\n')


def load_summaries(summary_dir: str) -> List[dict]:
    """
    Recursively load all JSON summary files from a directory (ex: downloaded workflow artifacts)

    :param summary_dir: directory containing JSON summary files
    :return: list of summary dictionaries sorted by identifier
    """
    summaries = []
    for path in glob.glob(os.path.join(summary_dir, '**', '*.json'), recursive=True):
        with open(path) as f:
            summaries.append(json.load(f))
    return sorted(summaries, key=lambda s: s.get('identifier', ''))


ACTIONS = ('create', 'update', 'replace', 'delete')


def build_plan_details(summary: dict, include_resources: bool = True) -> str:
    """
    Build a collapsed section for a single plan with the identifier and change counts as the header, and the
    resources changed underneath

    :param summary: summary dictionary
    :param include_resources: list the changed resources (False to keep the comment under the size limit)
    :return: markdown string
    """
    lists = [summary.get(key, []) for key in ACTIONS]
    counts = ', '.join(f'{len(items)} {label}' for items, label in
                       zip(lists, ('created', 'updated', 'replaced', 'destroyed')))
    output = f'<details><summary>🔄 <b>{summary["identifier"]}</b> {counts}</summary>\n'
    if include_resources:
        for items, heading in zip(lists, ('🛠️ Created', '🔀 Updated', '♻️ Replaced', '❌ Destroyed')):
            output = append_to_output(output, items, heading)
    else:
        output += '\n_Resource list omitted due to comment size limit, see the workflow run._\n'
    return output + '\n</details>\n\n'


def format_plan_count(reported: int, expected: Optional[List[str]]) -> str:
    """
    :param reported: number of plans that reported a summary
    :param expected: list of identifiers expected to have a summary
    :return: line comparing the number of plans reported to the number expected
    """
    if not expected:
        return f'**Plans reported:** {reported}'
    icon = '✅' if reported >= len(expected) else '❌'
    return f'**Plans reported:** {icon} {reported} of {len(expected)}'


def build_aggregate_output(summaries: List[dict], expected: Optional[List[str]] = None, run_url: str = '',
                           sha: str = '') -> str:
    """
    Build a single pull request comment summarizing many Terraform plans. A totals table is shown at the top,
    each plan with changes gets a section with its counts and the resources changed, plans with no
    changes are collapsed into one line.

    :param summaries: list of summary dictionaries
    :param expected: list of identifiers expected to have a summary, used to report missing (failed) plans
    :param run_url: link to the workflow run
    :param sha: commit sha the plans were run against
    :return: markdown string
    """
    changed = [s for s in summaries if has_changes(s)]
    unchanged = [s for s in summaries if not has_changes(s)]
    found = {s['identifier'] for s in summaries}
    missing = sorted(set(expected or []) - found)
    totals = {key: sum(len(s.get(key, [])) for s in changed) for key in ACTIONS}

    output = f'{AGGREGATE_MARKER}\n## Terraform Plan Summary\n\n'
    links = [f'`{sha[:7]}`'] if sha else []
    if run_url:
        links.append(f'[workflow run]({run_url})')
    if links:
        output += ' · '.join(links) + '\n\n'
    reported = len(found & set(expected)) if expected else len(summaries)
    output += format_plan_count(reported, expected) + '\n\n'

    output += '| Created | Updated | Replaced | Destroyed |\n| ---: | ---: | ---: | ---: |\n'
    output += '| ' + ' | '.join(str(totals[key]) for key in ACTIONS) + ' |\n\n'

    if missing:
        output += f'> [!CAUTION]\n> {len(missing)} plan(s) did not report a result (failed or cancelled):\n'
        output += ''.join(f'> - `{m}`\n' for m in missing) + '\n'
    if not changed and not missing:
        output += '🟢 No changes\n\n'

    footer = ''
    if unchanged:
        footer = f'<details><summary>🟢 {len(unchanged)} plan(s) with no changes</summary>\n\n' + \
                 ''.join(f'- `{s["identifier"]}`\n' for s in unchanged) + '\n</details>\n'

    # every plan always gets its section with counts, resource lists are added while they fit
    sections = [build_plan_details(s, include_resources=False) for s in changed]
    budget = MAX_COMMENT_LENGTH - len(output) - len(footer) - sum(len(d) for d in sections)
    for i, s in enumerate(changed):
        full = build_plan_details(s)
        extra = len(full) - len(sections[i])
        if extra <= budget:
            sections[i] = full
            budget -= extra
    output += ''.join(sections)

    if len(output) + len(footer) <= MAX_COMMENT_LENGTH:
        output += footer
    return output


def main_aggregate() -> None:
    """
    Entrypoint for aggregate mode. Combines JSON summaries from many plans into a single comment.

    :return: None
    """
    summary_dir = os.getenv('SUMMARY_DIR', '.')
    output_file = os.getenv('OUTPUT_FILE', 'terraform-pr-summary.txt')
    expected = json.loads(os.getenv('EXPECTED_IDENTIFIERS') or '[]')
    run_url = ''
    if os.getenv('GITHUB_RUN_ID'):
        run_url = f'{os.getenv("GITHUB_SERVER_URL")}/{os.getenv("GITHUB_REPOSITORY")}/actions/runs/' \
                  f'{os.getenv("GITHUB_RUN_ID")}'

    summaries = load_summaries(summary_dir)
    print(f'loaded {len(summaries)} summaries from {summary_dir}')
    output = build_aggregate_output(summaries, expected, run_url, os.getenv('HEAD_SHA', ''))
    write_output(output, output_file)
    write_github_output('has-changes', str(any(has_changes(s) for s in summaries)).lower())
    print(f'\n{output}\n')


def main() -> None:
    """
    Main entrypoint for this script. This will parse the Terraform plan file as JSON, get a list of resource
    changes, and create a summary string that can be added as a comment to a pull request.

    :return: None
    """
    if os.getenv('MODE') == 'aggregate':
        return main_aggregate()

    custom_identifier = os.getenv('IDENTIFIER')
    plan_file = os.getenv('PLAN_FILE')
    output_file = os.getenv('OUTPUT_FILE', 'terraform-pr-summary.txt')
    json_file = os.getenv('JSON_FILE', 'terraform-pr-summary.json')

    output = build_output_header(custom_identifier)
    plan_json = get_terraform_plan_json(plan_file)
    resource_changes = parse_resource_changes(plan_json)
    output = append_changes_to_output(output, resource_changes)
    write_output(output, output_file)

    summary = build_summary(custom_identifier, resource_changes)
    write_output(json.dumps(summary), json_file)
    write_github_output('has-changes', str(has_changes(summary)).lower())
    print(f'\n{output}\n')


if __name__ == '__main__':
    main()
