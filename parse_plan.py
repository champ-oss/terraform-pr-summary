import json
import sys
from typing import List


def parse_resource_changes(plan_json_file: str) -> List[dict]:
    with open(plan_json_file) as f:
        plan = json.loads(f.read())
        return plan.get('resource_changes', [])


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


def build_output(resource_changes: List[dict]) -> str:
    create = get_create_changes(resource_changes)
    update = get_update_changes(resource_changes)
    replace = get_replace_changes(resource_changes)
    delete = get_delete_changes(resource_changes)

    output = f'**Terraform Plan**\n'
    output += f'👉 {len(create)} to create, {len(update)} to update, ' \
              f'{len(replace)} to replace, {len(delete)} to destroy\n'
    output = append_to_output(output, create, '🛠️ Created')
    output = append_to_output(output, update, '🔀 Updated')
    output = append_to_output(output, replace, '♻️ Replaced')
    output = append_to_output(output, delete, '❌ Deleted')
    return output


def main():
    plan_json_file = sys.argv[1]
    resource_changes = parse_resource_changes(plan_json_file)
    print(build_output(resource_changes))


if __name__ == '__main__':
    main()
