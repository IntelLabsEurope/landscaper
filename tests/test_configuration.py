# Copyright (c) 2017, Intel Research and Development Ireland Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Tests for Configuration Manager
"""
import unittest
import mock
import os
from landscaper.utilities import configuration

from tests.test_utils import utils

CONFIGURATION_SECTION = 'general'
PHYSICAL_CONFIG = 'physical_layer'
# pylint: disable=W0212


class TestConfiguration(unittest.TestCase):
    """
    Unit tests for hwloc and cpuinfo retireval from DataClay.
    """

    @classmethod
    def setUpClass(cls):
        utils.create_test_config()

    @classmethod
    def tearDownClass(cls):
        utils.remove_test_config()

    def setUp(self):
        test_config = "tests/data/tmp_config.conf"
        self.conf_manager = configuration.ConfigurationManager(test_config)
        self.conf_manager.add_section(CONFIGURATION_SECTION)

    def test_getvar(self):
        """
        Tests that a val is retrieved correctly
        :return:
        """
        section = "general"
        variable = "flush"
        expected_value = "False"
        actual_value = self.conf_manager.get_variable(section, variable)
        self.assertEqual(expected_value, actual_value,
                         "Returned value does not match set value")

    def test_getvar_notexists(self):
        """
        Tests that a val is retrieved correctly
        :return:
        """
        section = "general"
        variable = "foo"
        actual_value = self.conf_manager.get_variable(section, variable)
        self.assertIsNone(actual_value,
                          "Returned value seems should have been None")

    def test_setvar(self):
        """
        Tests that a val is set correctly
        :return:
        """
        section = "general"
        variable = "test"
        expected_value = "foobar"
        self.conf_manager.set_variable(section, variable, expected_value)

        actual_value = self.conf_manager.get_variable(section, variable)
        self.assertEqual(expected_value, actual_value,
                         "Returned value does not match set value")

    def get_test_hwloc_folder():
        tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
        return tests_dir

    @mock.patch('landscaper.utilities.configuration.ConfigurationManager.get_hwloc_folder', side_effect=get_test_hwloc_folder)

    def test_get_machines(self, get_test_hwloc_folder_function):
        """
        Tests get_machines function
        """
        machines = self.conf_manager.get_machines()
        self.assertIn('machine-A', machines)

