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
""""
Tests for the neo4j graph database module.
"""
import unittest
import mock

from landscaper.graph_db import neo4j_db

# W0212 -  Access to a protected member
# pylint: disable=W0212


class TestUniqueAttributeNames(unittest.TestCase):
    """
    Tests for the unique_attribute_names method.
    """
    @mock.patch("landscaper.graph_db.neo4j_db.Neo4jGDB._get_db_connection")
    def setUp(self, mck_get_connection):
        mck_get_connection.return_value = None
        self.gdb = neo4j_db.Neo4jGDB(mock.Mock())

    def test_no_clash(self):
        """
        Give it a list of names that do not clash with any of the attributes
        in the attribute dictionary.
        """
        immutable_keys = ["name", "type", "category", "layer"]
        attributes = {"origin": "LGA", "destination": "LAX", "duration": "7"}
        unique_attributes = self.gdb._unique_attribute_names(immutable_keys,
                                                             attributes, "")
        self.assertEqual(attributes, unique_attributes)

    def test_single_key_single_clash(self):
        """
        Check a clash between an attribute key and an immutable key. This is a
        single clash as the key will not need to be modified more than once.
        """
        prefix = "component"
        immutable_keys = ["name", "type", "category", "layer"]
        attributes = {"name": "NIC", "address": "1234"}
        expected_attributes = {"component-name": "NIC", "address": "1234"}

        unique_attributes = self.gdb._unique_attribute_names(immutable_keys,
                                                             attributes,
                                                             prefix)
        self.assertNotEqual(attributes, unique_attributes)  # catch reference
        self.assertEqual(unique_attributes, expected_attributes)

    def test_single_key_double_clash(self):
        """
        Check a clash between an attribute key and an immutable key. This is a
        double clash as the key will need to be modified more than once.
        """
        prefix = 'NIC'
        immutable_keys = ["name", "type", "category", "layer"]
        attributes = {'type': 'nic', 'NIC-type': 'high', 'bw': '40'}
        expected_attributes = {'NIC-type_1': 'nic', 'NIC-type': 'high',
                               'bw': '40'}
        unique_attributes = self.gdb._unique_attribute_names(immutable_keys,
                                                             attributes,
                                                             prefix)
        self.assertEqual(unique_attributes, expected_attributes)

    def test_single_key_triple_clash(self):
        """
        Check a clash between an attribute key and an immutable key. This is a
        double clash as the key will need to be modified more than once.
        """
        prefix = 'machine'
        immutable_keys = ["name", "type", "category", "layer"]
        attributes = {'type': 'machine-a', 'machine-type': 'machine-b',
                      'machine-type_1': 'machine-c'}
        expected_attributes = {'machine-type_1': 'machine-c',
                               'machine-type': 'machine-b',
                               'machine-type_2': 'machine-a'}
        unique_attributes = self.gdb._unique_attribute_names(immutable_keys,
                                                             attributes,
                                                             prefix)
        self.assertEqual(unique_attributes, expected_attributes)

    def test_triple_key_single_clash(self):
        """
        Test with three clashing keys.
        """
        prefix = "cache"
        immutable_keys = ["name", "type", "category", "layer"]
        attributes = {"name": "cache", "type": "compute", "layer": "physical"}
        expected_attributes = {"cache-name": "cache", "cache-type": "compute",
                               "cache-layer": "physical"}
        unique_attributes = self.gdb._unique_attribute_names(immutable_keys,
                                                             attributes,
                                                             prefix)
        self.assertNotEqual(unique_attributes, attributes)
        self.assertEqual(expected_attributes, unique_attributes)
