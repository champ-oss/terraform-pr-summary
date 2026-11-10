import json
import os
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


class TestAggregate(unittest.TestCase):
    changed = {'identifier': 'env/a.tfvars', 'create': ['x'], 'update': [], 'replace': [], 'delete': ['y']}
    unchanged = {'identifier': 'env/b.tfvars', 'create': [], 'update': [], 'replace': [], 'delete': []}

    def test_build_summary(self):
        summary = main.build_summary('id', TestMain.test_resource_changes)
        self.assertEqual(['test_create'], summary['create'])
        self.assertEqual(['test_replace_1', 'test_replace_2'], summary['replace'])
        self.assertTrue(main.has_changes(summary))
        self.assertFalse(main.has_changes(main.build_summary('id', [])))

    def test_aggregate_output(self):
        output = main.build_aggregate_output([self.changed, self.unchanged], ['env/a.tfvars', 'env/b.tfvars',
                                             'env/c.tfvars'], 'https://run', 'abcdef123')
        self.assertTrue(output.startswith(main.AGGREGATE_MARKER))
        self.assertIn('`abcdef1` · [workflow run](https://run)', output)
        self.assertNotIn('[!WARNING]', output)
        self.assertNotIn('⚠️', output)
        self.assertIn('> - `env/c.tfvars`', output)
        self.assertIn('**Plans reported:** ❌ 2 of 3', output)
        # totals table
        self.assertIn('| Created | Updated | Replaced | Destroyed |', output)
        self.assertIn('| 1 | 0 | 0 | 1 |', output)
        # plans with changes are collapsed with the identifier and counts as the header
        self.assertIn('<details><summary><b>env/a.tfvars</b> 🔄 1 created, 0 updated, 0 replaced, 1 destroyed'
                      '</summary>\n\n**🛠️ Created**:\nx\n\n**❌ Destroyed**:\ny\n\n</details>', output)
        self.assertNotIn('Terraform Plan (', output)
        self.assertEqual(2, output.count('<details>'))
        self.assertNotIn('```', output)
        self.assertNotIn('<details open>', output)
        # no changes section is collapsed
        self.assertIn('<details><summary>🟢 1 plan(s) with no changes</summary>', output)
        # unchanged plans only appear in the collapsed no changes list
        self.assertNotIn('<code>env/b.tfvars</code>', output)

    def test_aggregate_no_changes(self):
        output = main.build_aggregate_output([self.unchanged])
        self.assertIn('🟢 No changes', output)
        self.assertIn('| 0 | 0 | 0 | 0 |', output)
        self.assertNotIn('🔄', output)
        self.assertIn('**Plans reported:** 1\n', output)

    def test_plan_count(self):
        self.assertEqual('**Plans reported:** ✅ 2 of 2',
                         main.format_plan_count(2, ['env/a.tfvars', 'env/b.tfvars']))
        output = main.build_aggregate_output([self.changed, self.unchanged], ['env/a.tfvars', 'env/b.tfvars'])
        self.assertIn('**Plans reported:** ✅ 2 of 2', output)
        self.assertNotIn('[!CAUTION]', output)

    def test_aggregate_truncates(self):
        big = [dict(self.changed, identifier=f'env/{i}.tfvars', create=['r' * 100] * 50) for i in range(50)]
        output = main.build_aggregate_output(big)
        self.assertLessEqual(len(output), main.MAX_COMMENT_LENGTH)
        self.assertIn('Resource list omitted due to comment size limit', output)
        # every plan keeps its section and counts even when resource lists are omitted
        self.assertEqual(50, output.count('<summary><b>env/'))
        self.assertEqual(50, output.count('🔄 50 created, 0 updated, 0 replaced, 1 destroyed'))
        self.assertIn('| 2500 | 0 | 0 | 50 |', output)

    def test_load_summaries_and_main_aggregate(self):
        os.makedirs('agg/tf-summary-1', exist_ok=True)
        os.makedirs('agg/tf-summary-2', exist_ok=True)
        with open('agg/tf-summary-1/terraform-pr-summary.json', 'w') as f:
            json.dump(self.unchanged, f)
        with open('agg/tf-summary-2/terraform-pr-summary.json', 'w') as f:
            json.dump(self.changed, f)
        self.assertEqual(['env/a.tfvars', 'env/b.tfvars'], [s['identifier'] for s in main.load_summaries('agg')])

        os.environ.update({'MODE': 'aggregate', 'SUMMARY_DIR': 'agg', 'OUTPUT_FILE': 'agg.txt'})
        try:
            main.main()
        finally:
            for key in ('MODE', 'SUMMARY_DIR', 'OUTPUT_FILE'):
                os.environ.pop(key)
        with open('agg.txt') as f:
            self.assertIn('| 1 | 0 | 0 | 1 |', f.read())
