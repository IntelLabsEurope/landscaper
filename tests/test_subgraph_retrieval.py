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
Integration tests for the get subgraph feature.
"""
import json
import logging
import os
import unittest

from networkx.readwrite import json_graph

from landscaper import landscape_manager
from tests.test_utils import utils


class TestGetSubGraph(unittest.TestCase):
    """
    Integration tests for subgraph retrieval feature.  Uses the
    test_landscape.json graph to validate that the correct graphs are being
    retrieved.
    """
    landscape_file = "tests/data/test_landscape.json"
    subgraph_file = "tests/data/test_subgraph.json"

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
        self.events = {"start": 1502811001,
                       "first_delete": 1502818001,
                       "second_delete": 1502825001,
                       "first_add": 1502828001}

    def test_node_structure(self):
        """
        Tests that nodes are being packed as expected. The first test node is
        normal and the second node contains a renamed attribute.
        """
        node = "neutron-port-1"
        node_structure = {"category": "network", "layer": "virtual",
                          "name": "neutron-port-1", "ip": "UNDEFINED",
                          "mac": "UNDEFINED", "type": "vnic"}
        node_2 = "machine-A_eth23_0"
        node_structure_2 = {"category": "network", "layer": "physical",
                            "name": "machine-A_eth23_0", "osdev_type": "2",
                            "allocation": "machine-A", "type": "osdev_network",
                            "address": "54:6a:00:59:d6:33",
                            "osdev_network-name": "eth23"}

        graph = self.graph_db.get_subgraph("stack-1", json_out=False)

        self.assertEqual(graph.node[node], node_structure)
        self.assertEqual(graph.node[node_2], node_structure_2)

    def test_retrieve_living_stack(self):
        """
        Retrieve a stack that exists.
        """
        timestamp = self.events["start"] + 60
        stack = "e5a7ec3e-7b25-478c-a1f1-8dc472444a3a"
        subgraph = self.graph_db.get_subgraph(stack, timestamp, json_out=False)
        machines = self.graph_nodes(subgraph, "machine")

        # Only one machine attached
        self.assertEqual(machines, ["machine-I"])

        # All physical layer nodes are for machine-I
        for _, node in subgraph.nodes(data=True):
            if node["layer"] == "physical" and node["type"] != "switch":
                self.assertEqual(node["allocation"], "machine-I")

        # 43 nodes in the subgraph.
        self.assertEqual(len(subgraph.node), 43)

    def test_retrieve_dead_stack(self):
        """
        Retrieve a stack that is dead.
        """
        timestamp = self.events["second_delete"] + 60
        stack = "aa9825f5-4618-4fa2-8306-e4045837f489"
        subgraph = self.graph_db.get_subgraph(stack, timestamp, json_out=False)
        self.assertIsNone(subgraph)

    def test_subgraph_structure(self):
        """
        Check the subgraph structure.
        """
        timestamp = self.events["start"] + 60
        stack = "e5a7ec3e-7b25-478c-a1f1-8dc472444a3a"
        subgraph = self.graph_db.get_subgraph(stack, timestamp, json_out=False)
        expected_subgraph = load_subgraph(self.subgraph_file)

        changes = utils.compare_graph(expected_subgraph, subgraph)
        for _, change in changes.iteritems():
            self.assertEqual(change, [])

    def test_subgraph_timeframe_living(self):
        """
        Ensure we get a subgraph back over the time. Grab a stack that is alive
        for the duration of the timeframe.
        """
        timestamp = self.events["start"] + 60
        timeframe = self.events["first_add"] + 600 - timestamp
        stack = "e5a7ec3e-7b25-478c-a1f1-8dc472444a3a"
        subgraph = self.graph_db.get_subgraph(stack, timestamp,
                                              timeframe, json_out=False)
        expected_subgraph = load_subgraph(self.subgraph_file)

        changes = utils.compare_graph(expected_subgraph, subgraph)
        for _, change in changes.iteritems():
            self.assertEqual(change, [])

    def test_stack_alive_at_beginning(self):
        """
        Grab a subgraph which is alive at the start of the timeframe, but has
        been deleted by the end of the timeframe. We will get nothing, as the
        subgraph uuid must be alive for the duration of the timeframe.
        """
        timestamp = self.events["start"] + 60
        timeframe = self.events["first_add"] + 600 - timestamp
        stack = "d1ea0f88-7e65-42fc-864f-915d12d63289"
        subgraph = self.graph_db.get_subgraph(stack, timestamp,
                                              timeframe, json_out=False)
        self.assertIsNone(subgraph)

    def test_stack_alive_at_end(self):
        """
        Retrieve a subgraph which doesn't exist at the start of the timeframe,
        but has been created by the end of the timeframe. We will get nothing,
        as the subgraph uuid must be alive for the duration of the timeframe.
        """
        timestamp = self.events["start"] + 60
        timeframe = self.events["first_add"] + 600 - timestamp
        stack = "stack-1"
        subgraph = self.graph_db.get_subgraph(stack, timestamp,
                                              timeframe, json_out=False)
        self.assertIsNone(subgraph)

    def test_grab_single_machine(self):
        """
        Grab just a machine and all of its constituent components from the
        database.
        """
        strt = self.events["start"] + 60
        machine = self.graph_db.get_subgraph("machine-A", strt, json_out=False)
        for _, node_data in machine.nodes(data=True):
            if node_data['type'] != 'switch':
                self.assertEqual(node_data["allocation"], "machine-A")
                self.assertEqual(node_data["layer"], "physical")

    def tearDown(self):
        self.graph_db.delete_all()

    @staticmethod
    def graph_nodes(graph, node_type, attribute=None):
        """
        Return the all nodes from the graph of type 'node_type'.
        :param graph: Graph to search.
        :param node_type: Type of node to search for.
        :param attribute: If none then the node ids are returned, if set then
        the attribute type for that node is returned.
        :return: list of nodes.
        """
        graph_nodes = []
        for node_id, node_data in graph.nodes(data=True):
            if node_data["type"] == node_type:
                if attribute:
                    graph_nodes.append(node_data[attribute])
                else:
                    graph_nodes.append(node_id)
        return graph_nodes


def load_subgraph(the_file):
    """
    Loads the test subgraph from a file.
    :param the_file: File name.
    :return: Networkx graph.
    """
    graph_data = json.load(open(the_file))
    networkx_graph = json_graph.node_link_graph(graph_data, directed=True)
    return networkx_graph
