import json
import unittest
from unittest.mock import MagicMock

import main


class TestMain(unittest.TestCase):
    test_resource_changes = [
        {
            'address': 'test_create',
            'change': {
                'actions': ['create']
            }
        },
        {
            'address': 'test_update',
            'change': {
                'actions': ['update']
            }
        },
        {
            'address': 'test_delete',
            'change': {
                'actions': ['delete']
            }
        },
        {
            'address': 'test_replace_1',
            'change': {
                'actions': ['delete', 'create']
            }
        },
        {
            'address': 'test_replace_2',
            'change': {
                'actions': ['create', 'delete']
            }
        }
    ]

    def test_parse_resource_changes(self):
        self.assertEqual(['foo'], main.parse_resource_changes('{"resource_changes":["foo"]}'))

    def test_parse_resource_changes_with_json_exception(self):
        with self.assertRaises(Exception):
            main.parse_resource_changes('foo')

    def test_get_create_changes(self):
        self.assertEqual(['test_create'], main.get_create_changes(self.test_resource_changes))

    def test_get_update_changes(self):
        self.assertEqual(['test_update'], main.get_update_changes(self.test_resource_changes))

    def test_get_delete_changes(self):
        self.assertEqual(['test_delete'], main.get_delete_changes(self.test_resource_changes))

    def test_get_replace_changes(self):
        self.assertEqual(['test_replace_1', 'test_replace_2'], main.get_replace_changes(self.test_resource_changes))

    def test_append_to_output(self):
        output = main.append_to_output('', ['test1'], 'test')
        self.assertEqual('\n**test**:\ntest1\n', output)

    def test_append_to_output_with_no_items(self):
        output = main.append_to_output('', [], 'test')
        self.assertEqual('', output)

    def test_build_output_header(self):
        self.assertEqual('**Terraform Plan**\n\n', main.build_output_header(''))

    def test_build_output_header_with_identifier(self):
        self.assertEqual('**Terraform Plan (test)**\n\n', main.build_output_header('test'))

    def test_append_changes_to_output(self):
        output = main.append_changes_to_output('', self.test_resource_changes)
        self.assertEqual('👉 1 to create, 1 to update, 2 to replace, 1 to destroy\n'
                         '\n'
                         '**🛠️ Created**:\n'
                         'test_create\n'
                         '\n'
                         '**🔀 Updated**:\n'
                         'test_update\n'
                         '\n'
                         '**♻️ Replaced**:\n'
                         'test_replace_1\n'
                         'test_replace_2\n'
                         '\n'
                         '**❌ Deleted**:\n'
                         'test_delete\n', output)

    def test_write_output(self):
        test_file = 'test.txt'
        main.write_output('test', test_file)
        with open('test.txt') as f:
            self.assertEqual('test', f.read())

    def test_main(self):
        mock_get_terraform_plan_json = MagicMock()
        mock_get_terraform_plan_json.return_value = json.dumps({'resource_changes': self.test_resource_changes})
        main.get_terraform_plan_json = mock_get_terraform_plan_json

        main.main()

        expected_output = '**Terraform Plan**\n' \
                          '\n' \
                          '👉 1 to create, 1 to update, 2 to replace, 1 to destroy\n' \
                          '\n' \
                          '**🛠️ Created**:\n' \
                          'test_create\n' \
                          '\n' \
                          '**🔀 Updated**:\n' \
                          'test_update\n' \
                          '\n' \
                          '**♻️ Replaced**:\n' \
                          'test_replace_1\n' \
                          'test_replace_2\n' \
                          '\n' \
                          '**❌ Deleted**:\n' \
                          'test_delete\n'

        with open('terraform-pr-summary.txt') as f:
            self.assertEqual(expected_output, f.read())
