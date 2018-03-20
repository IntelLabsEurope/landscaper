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
import time
import mock

from py2neo import Node

from landscaper.graph_db import neo4j_db
from landscaper import landscape_manager

from tests.test_utils import utils

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


class TestNodeUpdateIntegration(unittest.TestCase):
    """
    Integration tests for the update_node method.
    """
    landscape_file = "tests/data/test_landscape_with_states.json"

    def setUp(self):
        utils.create_test_config()
        manager = landscape_manager.LandscapeManager(utils.TEST_CONFIG_FILE)
        self.graph_db = manager.graph_db
        self.graph_db.delete_all()
        self.graph_db.load_test_landscape(self.landscape_file)

    def tearDown(self):
        self.graph_db.delete_all()
        utils.remove_test_config()

    def test_state_updated(self):
        """
        Test that a new state node is updated in the landscape.
        """
        node_id = 'machine-A'
        old_state = self._node_state_attributes(node_id)
        attrs = {"A": 'apple', "B": 'banana'}
        self.graph_db.update_node(node_id, time.time(), attrs)
        new_state = self._node_state_attributes(node_id)

        self.assertNotEqual(old_state, attrs)
        self.assertEqual(new_state, attrs)

    def test_extra_attributes(self):
        """
        Test that extra attributes are added to the state.
        """
        # VM node in landscape.
        node_id = "1ffaedbf-719a-4327-a14e-ed7b8564fb4e"
        old_state = self._node_state_attributes(node_id)

        # UPDATE
        attrs = {'h': 'happy', 'i': 'ink'}
        self.graph_db.update_node(node_id, time.time(), extra_attrs=attrs)

        # New state attrs from landscape
        new_state = self._node_state_attributes(node_id)
        attrs.update(old_state)
        expected_state = attrs
        self.assertEqual(new_state, expected_state)

    def test_state_extra(self):
        """
        Test that when there is a state and extra attrs, that they are both
        combined into a new state.
        """
        # stack from the landscape.
        node_id = "stack-1"
        old_state = self._node_state_attributes(node_id)

        # UPDATE
        state_attrs = {"m": "motor", "n": "nose"}
        extra_attrs = {"r": "rock", "s": "snow"}
        timestamp = time.time()
        self.graph_db.update_node(node_id, timestamp, state_attrs, extra_attrs)

        # Assertions
        new_state = self._node_state_attributes(node_id)
        state_attrs.update(extra_attrs)
        expected_attrs = state_attrs
        self.assertNotEqual(old_state, expected_attrs)
        self.assertEqual(new_state, expected_attrs)

    def test_state_extra_priority(self):
        """
        Test that when given a state and extra attributes with matching
        attributes that extra attributes takes priority.
        """
        # stack from the landscape.
        node_id = "machine-E"
        old_state = self._node_state_attributes(node_id)

        # UPDATE
        state_attrs = {"j": "juice", "k": "kilowatt"}
        extra_attrs = {"k": "kilometer", "l": "lights"}
        timestamp = time.time()
        self.graph_db.update_node(node_id, timestamp, state_attrs, extra_attrs)

        # Assertions
        new_state = self._pop_identity(self._node_state_attributes(node_id))
        expected_attrs = {"k": "kilometer", "l": "lights", "j": "juice"}
        self.assertNotEqual(old_state, expected_attrs)
        self.assertEqual(new_state, expected_attrs)

    def _node_state_attributes(self, node_id):
        """
        returns a node from the landscape by id.
        :param node_id: The node to grab.
        :return: a node from the landscape by id.
        """
        graph = self.graph_db.get_node_by_uuid_web(node_id, json_out=False)
        node_attrs = graph.nodes(data=True)[0][1]
        return self._pop_identity(node_attrs)

    @staticmethod
    def _pop_identity(node_attributes):
        """
        removes the identity attributes.
        """
        trimmed_attributes = node_attributes.copy()
        for attr_key, _ in node_attributes.iteritems():
            if attr_key in ['name', 'type', 'layer', 'category']:
                trimmed_attributes.pop(attr_key)
        return trimmed_attributes


class TestNodeUpdateUnit(unittest.TestCase):
    """
    Unit tests for the node_update method.
    """

    def setUp(self):
        mck_manager = mock.MagicMock()
        mck_manager.get_neo4j_credentials.return_value = (1, 1)

        self.neo4j = neo4j_db.Neo4jGDB(mck_manager)
        self.identity = {'a': 'b'}
        self.neo4j.get_node_by_uuid = mock.Mock(return_value=self.identity)

        # Mock some methods.
        self.neo4j.graph_db = mock.MagicMock()
        self.neo4j._create_edge = mock.MagicMock()
        self.neo4j._expire_edge = mock.MagicMock()

    def test_nothing_to_update(self):
        """
        Test that when there is no state and no extra_attributes that None is
        returned.
        """
        identity, msg = self.neo4j.update_node('id', 0)
        self.assertIsNotNone(identity)
        self.assertFalse('success' in msg)

    def test_unknown_node(self):
        """
        Test that if a node is not found in the landscape that None is
        returned.
        """
        self.neo4j.get_node_by_uuid = mock.Mock(return_value=None)
        identity, _ = self.neo4j.update_node('id', 0, {'car': 'VW'})
        self.assertIsNone(identity)

    def test_state_update(self):
        """
        Test that if given a state we update node with the new state.
        """
        # Setup the NEO4J Nodes.
        now_ts = time.time()

        # New state
        state = {'A': 2, 'B': 4, 'C': 6}

        # Old state
        old_state_n = Node('blah', **{'A': 1, 'B': 3, 'C': 5})
        edge_tuple = (old_state_n, None)
        self.neo4j._get_state_node = mock.MagicMock(return_value=edge_tuple)

        # UPDATE
        identity, _ = self.neo4j.update_node('node', now_ts, state)

        # Check that the new node has been attached to the identity node.
        call_args = self.neo4j._create_edge.call_args_list[0][0]
        self.assertEqual(identity, call_args[0])
        self.assertEqual(state, dict(call_args[1]))
        self.assertEqual(now_ts, call_args[2])
        self.assertEqual('STATE', call_args[3])

    def test_extra_attributes(self):
        """
        Test that extra_attributes are added to a new state and concatenated
        with the old state.
        """
        now_ts = time.time()

        # extra attributes
        attrs = {'x': 24, 'y': 25, 'z': 26}

        # Build old state node.
        old_state_n = Node('blah', **{'A': 1, 'B': 3, 'C': 5})
        edge_tuple = (old_state_n, None)
        self.neo4j._get_state_node = mock.MagicMock(return_value=edge_tuple)

        # UPDATE
        identity, _ = self.neo4j.update_node('node', now_ts, extra_attrs=attrs)

        attrs.update({'A': 1, 'B': 3, 'C': 5})
        expected_attrs = attrs
        # Assertions.
        call_args = self.neo4j._create_edge.call_args_list[0][0]
        self.assertEqual(identity, call_args[0])
        self.assertEqual(expected_attrs, dict(call_args[1]))
        self.assertEqual(now_ts, call_args[2])
        self.assertEqual('STATE', call_args[3])

    def test_state_with_extra(self):
        """
        Test that if there is a state and extra attributes that they are both
        added to the new node.
        """
        now_ts = time.time()

        # Mock old state
        old_state_n = Node('blah', **{'A': 1, 'B': 3, 'C': 5})
        edge_tuple = (old_state_n, None)
        self.neo4j._get_state_node = mock.MagicMock(return_value=edge_tuple)

        # new state and extra attributes
        state = {'a': 1, 'b': 2, 'c': 3}
        attrs = {'x': 24, 'y': 25, 'z': 26}
        combined = {'a': 1, 'b': 2, 'c': 3, 'x': 24, 'y': 25, 'z': 26}

        # UPDATE
        identity, _ = self.neo4j.update_node('node', now_ts, state, attrs)

        # Assertions
        call_args = self.neo4j._create_edge.call_args_list[0][0]
        self.assertEqual(identity, call_args[0])
        self.assertEqual(combined, dict(call_args[1]))
        self.assertEqual(now_ts, call_args[2])
        self.assertEqual('STATE', call_args[3])

    def test_state_with_extra_crossover(self):
        """
        Test that if state and extra have overlapping attributes then extra
        takes priority.
        """
        now_ts = time.time()

        # Mock old state
        old_state_n = Node('blah', **{'A': 1})
        edge_tuple = (old_state_n, None)
        self.neo4j._get_state_node = mock.MagicMock(return_value=edge_tuple)

        # new state and extra attributes
        state = {'a': 1, 'b': 2, 'c': 3, 'k': 7}
        attrs = {'k': 14, 'x': 24, 'y': 25, 'z': 26}
        combined = {'a': 1, 'b': 2, 'c': 3, 'x': 24, 'y': 25, 'z': 26, 'k': 14}

        # UPDATE
        identity, _ = self.neo4j.update_node('node', now_ts, state, attrs)

        call_args = self.neo4j._create_edge.call_args_list[0][0]
        self.assertEqual(identity, call_args[0])
        self.assertEqual(combined, dict(call_args[1]))
        self.assertEqual(now_ts, call_args[2])
        self.assertEqual('STATE', call_args[3])

    def test_empty_extra_attrs(self):
        """
        Test that if the extra attributes list is empty and no state that None
        is returned.
        """
        identity, msg = self.neo4j.update_node('id', 0, extra_attrs={})
        self.assertIsNotNone(identity)
        self.assertFalse('success' in msg)

    def test_unchanged_state(self):
        """
        If the new state does not differ from the old state then don't try to
        update.
        """
        now_ts = time.time()
        self.neo4j._create_edge = mock.MagicMock()

        # Mock old state
        old_state_n = Node('old', **{'a': 'ok', 'b': 4, 'c': 'u'})
        edge_tuple = (old_state_n, None)
        self.neo4j._get_state_node = mock.MagicMock(return_value=edge_tuple)

        # new state and extra attributes
        state = {'a': 'ok', 'c': 'u'}
        attrs = {'b': 4}

        # UPDATE
        self.neo4j.update_node('node', now_ts, state, attrs)

        # Assertions (Never Gets this far.)
        self.neo4j._create_edge.assert_not_called()

    def test_old_state_expired(self):
        """
        Once a new state is created the old state should be expired.
        """
        now_ts = time.time()

        # Mock old state
        old_state_n = Node('old', **{'a': 'ok', 'b': 4, 'c': 'u'})
        old_edge_r = 'i.am.edge'
        edge_tuple = (old_state_n, old_edge_r)
        self.neo4j._get_state_node = mock.MagicMock(return_value=edge_tuple)

        # new state and extra attributes
        state = {'a': 'ok', 'c': 'u'}

        # UPDATE
        self.neo4j.update_node('node', now_ts, state)

        # Assertions (Never Gets this far.)
        self.assertTrue(self.neo4j._create_edge.called)
        self.neo4j._expire_edge.assert_called_once_with(old_edge_r, now_ts)
