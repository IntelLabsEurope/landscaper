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
Integration tests for get_node_by_uuid_web and get_node_by_properties_web
"""
import json
import logging
import unittest

from networkx.readwrite import json_graph

from landscaper import landscape_manager
from tests.test_utils import utils


class TestGetNodeByUUID(unittest.TestCase):
    """
    Integration Tests for get_node_by_uuid_web
    """
    landscape_file = "tests/data/test_landscape_with_states.json"

    @classmethod
    def setUpClass(cls):
        logging.disable(logging.CRITICAL)
        utils.create_test_config()

    @classmethod
    def tearDownClass(cls):
        logging.disable(logging.NOTSET)
        utils.remove_test_config()

    def setUp(self):
        manager = landscape_manager.LandscapeManager(utils.TEST_CONFIG_FILE)

        self.graph_db = manager.graph_db
        self.graph_db.delete_all()
        self.graph_db.load_test_landscape(self.landscape_file)

    def tearDown(self):
        self.graph_db.delete_all()

    def test_node_structure(self):
        """
        Ensure the node structure is correct.
        """
        node = "96449fb1-0143-4d61-9d84-0a2fd0aa30c1"
        node_structure = {"category": "network", "layer": "virtual",
                          "name": "96449fb1-0143-4d61-9d84-0a2fd0aa30c1",
                          "ip": "10.2.32.169", "mac": "fa:16:3e:7c:5c:66",
                          "type": "vnic"}
        graph_serialised = self.graph_db.get_node_by_uuid_web(node)
        graph = json_graph.node_link_graph(json.loads(graph_serialised),
                                           directed=True)
        self.assertEqual(len(graph.node), 1)
        self.assertEqual(graph.node[node], node_structure)

    def test_structure_renamed(self):
        """
        Ensure the node structure is correct where attributes have been
        renamed.
        """
        node = "machine-A_eth23_0"
        node_structure = {"category": "network", "layer": "physical",
                          "name": "machine-A_eth23_0", "osdev_type": "2",
                          "allocation": "machine-A", "type": "osdev_network",
                          "address": "54:6a:00:59:d6:33",
                          "osdev_network-name": "eth23"}
        graph = _deserialize(self.graph_db.get_node_by_uuid_web(node))
        self.assertEqual(len(graph.node), 1)
        self.assertEqual(graph.node[node], node_structure)


class TestGetNodeByProperties(unittest.TestCase):
    """
    Integration Tests for get_node_by_properties_web
    """
    landscape_file = "tests/data/test_landscape_with_states.json"

    @classmethod
    def setUpClass(cls):
        utils.create_test_config()
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        utils.remove_test_config()
        logging.disable(logging.NOTSET)

    def setUp(self):
        manager = landscape_manager.LandscapeManager(utils.TEST_CONFIG_FILE)
        self.graph_db = manager.graph_db
        self.graph_db.delete_all()
        self.graph_db.load_test_landscape(self.landscape_file)

    def tearDown(self):
        self.graph_db.delete_all()

    def test_all_stacks(self):
        """
        Check that we get back the correct number of stacks that survived.
        """
        prop = ("type", "stack")
        graph = _deserialize(self.graph_db.get_node_by_properties_web(prop))
        self.assertEqual(len(graph.node), 2)

    def test_structure(self):
        """
        Check that the node structure is ok.
        """
        node_structure = {"category": "compute", "layer": "service",
                          "name": "stack-1", "stack_name": "yew",
                          "template": "<>", "type": "stack"}
        node = "stack-1"
        prop = ("name", node)
        graph = _deserialize(self.graph_db.get_node_by_properties_web(prop))

        self.assertEqual(len(graph), 1)
        self.assertEqual(graph.node[node], node_structure)

    def test_prop_structure_renamed(self):
        """
        Check that the structure is ok where attributes have been renamed.
        """
        node = "machine-A_eth23_0"
        node_structure = {"category": "network", "layer": "physical",
                          "name": "machine-A_eth23_0", "osdev_type": "2",
                          "allocation": "machine-A", "type": "osdev_network",
                          "address": "54:6a:00:59:d6:33",
                          "osdev_network-name": "eth23"}
        prop = ("name", node)
        graph = _deserialize(self.graph_db.get_node_by_properties_web(prop))
        self.assertEqual(len(graph), 1)
        self.assertEqual(graph.node[node], node_structure)


def _deserialize(str_graph):
    """
    Converts a networkx formatted json string to a networkx graph object.
    :param str_graph: networkx formatted json string graph.
    :return: networkx graph object.
    """
    return json_graph.node_link_graph(json.loads(str_graph), directed=True)
