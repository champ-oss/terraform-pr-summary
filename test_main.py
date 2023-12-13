import unittest

from main import *


class TestMain(unittest.TestCase):
    pass

    def test_build_output_header(self):
        self.assertEqual('**Terraform Plan**\n\n', build_output_header(''))

    def test_build_output_header_with_identifier(self):
        self.assertEqual('**Terraform Plan (test)**\n\n', build_output_header('test'))
