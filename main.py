import json
import os
import subprocess
from json import JSONDecodeError
from typing import List


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
            if resource['change']['actions'] == ["delete", "create"] or
            resource['change']['actions'] == ["create", "delete"]]


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

    output += f'👉 {len(create)} to create, {len(update)} to update, ' \
              f'{len(replace)} to replace, {len(delete)} to destroy\n'

    output = append_to_output(output, create, '🛠️ Created')
    output = append_to_output(output, update, '🔀 Updated')
    output = append_to_output(output, replace, '♻️ Replaced')
    output = append_to_output(output, delete, '❌ Deleted')
    return output


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


def main() -> None:
    """
    Main entrypoint for this script. This will parse the Terraform plan file as JSON, get a list of resource
    changes, and create a summary string that can be added as a comment to a pull request.

    :return: None
    """
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
