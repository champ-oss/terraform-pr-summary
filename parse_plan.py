import json
import os
import subprocess
from json import JSONDecodeError
from typing import List


def get_terraform_plan_json(plan_file_path: str) -> str:
    command = ['terraform', 'show', '-json', plan_file_path]
    print('running command: ' + ' '.join(command))
    return subprocess.run(command, stdout=subprocess.PIPE).stdout.decode('utf-8')


def parse_resource_changes(plan_json: str) -> List[dict]:
    try:
        plan = json.loads(plan_json)
        return plan.get('resource_changes', [])
    except JSONDecodeError:
        print('Failed to parse Terraform plan JSON, did you run terraform init?')
        raise Exception


# https://developer.hashicorp.com/terraform/internals/json-format#change-representation
def get_create_changes(resource_changes: List[dict]) -> List[str]:
    return [resource['address'] for resource in resource_changes
            if resource['change']['actions'] == ['create']]


def get_update_changes(resource_changes: List[dict]) -> List[str]:
    return [resource['address'] for resource in resource_changes
            if resource['change']['actions'] == ['update']]


def get_delete_changes(resource_changes: List[dict]) -> List[str]:
    return [resource['address'] for resource in resource_changes
            if resource['change']['actions'] == ['delete']]


def get_replace_changes(resource_changes: List[dict]) -> List[str]:
    return [resource['address'] for resource in resource_changes
            if resource['change']['actions'] == ["delete", "create"] or
            resource['change']['actions'] == ["create", "delete"]]


def append_to_output(output: str, items: List[str], description: str):
    if not items:
        return output
    output += f'\n**{description}**:\n'
    for item in items:
        output += f'{item}\n'
    return output


def build_output_header(custom_identifier: str) -> str:
    if custom_identifier:
        print(f'using custom identifier: {custom_identifier}')
        return f'**Terraform Plan ({custom_identifier})**\n\n'
    return f'**Terraform Plan**\n\n'


def append_changes_to_output(output: str, resource_changes: List[dict]) -> str:
    create = get_create_changes(resource_changes)
    update = get_update_changes(resource_changes)
    replace = get_replace_changes(resource_changes)
    delete = get_delete_changes(resource_changes)

    output += f'👉 {len(create)} to create, {len(update)} to update, ' \
              f'{len(replace)} to replace, {len(delete)} to destroy\n'

    output = append_to_output(output, create, '🛠️ Created')
    output = append_to_output(output, update, '🔀 Updated')
    output = append_to_output(output, replace, '♻️ Replaced')
    output = append_to_output(output, delete, '❌ Deleted')
    return output


def write_output(output: str, file_name: str) -> None:
    print(f'writing output to file: {file_name}')
    with open(file_name, 'w') as f:
        f.write(output)


def main():
    custom_identifier = os.getenv('IDENTIFIER')
    plan_file = os.getenv('PLAN_FILE')
    output_file = os.getenv('OUTPUT_FILE')

    output = build_output_header(custom_identifier)
    plan_json = get_terraform_plan_json(plan_file)
    resource_changes = parse_resource_changes(plan_json)
    output = append_changes_to_output(output, resource_changes)
    write_output(output, output_file)
    print(f'\n{output}\n')


if __name__ == '__main__':
    main()
