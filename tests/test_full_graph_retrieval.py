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
Integration tests for the get graph feature.
"""
import logging
import unittest

from landscaper import landscape_manager
from tests.test_utils import utils


class TestGetGraph(unittest.TestCase):
    """
    Integration tests for get_graph. graph retrieval method.  Uses the
    test_landscape.json graph to validate that the correct graphs are being
    retrieved.
    """
    landscape_file = "tests/data/test_landscape_with_states.json"

    @classmethod
    def setUpClass(cls):
        """
        These tests connect to a running graph database and so for safety
        reasons this needs to be explicitly set.
        """
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

    def tearDown(self):
        self.graph_db.delete_all()

    def test_initial_stacks(self):
        """
        Test that all stacks are there.
        """
        start_time = self.events["start"] + 60
        graph = self.graph_db.get_graph(start_time, json_out=False)
        stacks = self.graph_nodes(graph, "stack", "stack_name")

        self.assertEqual(len(stacks), 4)
        self.assertEqual(set(["alder", "elm", "cedar", "birch"]), set(stacks))

    def test_query_after_delete(self):
        """
        Test that only two stacks are there.
        """
        first_delete_time = self.events["first_delete"] + 60
        graph = self.graph_db.get_graph(first_delete_time, json_out=False)
        stacks = self.graph_nodes(graph, "stack", "stack_name")
        self.assertEqual(len(stacks), 2)
        self.assertEqual(set(["alder", "elm"]), set(stacks))

    def test_query_after_second_delete(self):
        """
        Test that there is only 1 stack left.
        """
        second_delete_time = self.events["second_delete"] + 60
        graph = self.graph_db.get_graph(second_delete_time, json_out=False)
        stacks = self.graph_nodes(graph, "stack", "stack_name")
        self.assertEqual(len(stacks), 1)
        self.assertEqual(["elm"], stacks)

    def test_query_after_first_add(self):
        """
        After a stack has been added ensure that there are 2 stacks left.
        """
        first_add_time = self.events["first_add"] + 60
        graph = self.graph_db.get_graph(first_add_time, json_out=False)
        stacks = self.graph_nodes(graph, "stack", "stack_name")
        self.assertEqual(len(stacks), 2)
        self.assertItemsEqual(["elm", "yew"], stacks)

    def test_timeframe_immortal_stacks(self):
        """
        Test which stack has been alive from the beginning to the end.  This
        is done by setting the timestamp to the start and setting the
        timeframe to greater than the duration of the last event.
        """
        timestamp = self.events["start"] + 60
        timeframe = self.events["first_add"] + 10 - timestamp
        graph = self.graph_db.get_graph(timestamp, timeframe, json_out=False)
        stacks = self.graph_nodes(graph, "stack", "stack_name")
        self.assertEqual(len(stacks), 1)
        self.assertEqual(["elm"], stacks)  # Only elm lives forever.

    def test_timeframe_after_delete(self):
        """
        Test which stacks survived the first delete.
        """
        timestamp = self.events["start"] + 60
        timeframe = self.events["first_delete"] + 10 - timestamp
        graph = self.graph_db.get_graph(timestamp, timeframe, json_out=False)
        stacks = self.graph_nodes(graph, "stack", "stack_name")
        self.assertEqual(len(stacks), 2)
        self.assertEqual(["elm", "alder"], stacks)

    def test_timeframe_after_first_add(self):
        """
        Test which stacks were alive for 10 minutes after the first add.
        """
        timestamp = self.events["first_add"] + 60
        timeframe = self.events["first_add"] + 600 - timestamp
        graph = self.graph_db.get_graph(timestamp, timeframe, json_out=False)
        stacks = self.graph_nodes(graph, "stack", "stack_name")
        self.assertEqual(len(stacks), 2)
        self.assertItemsEqual(["elm", "yew"], stacks)

    def test_nodes_added(self):
        """
        Test that the added nodes are correctly retrieved and connected.
        """
        before_time = self.events["second_delete"] + 60
        after_time = self.events["first_add"] + 60
        before_add = self.graph_db.get_graph(before_time, json_out=False)
        after_add = self.graph_db.get_graph(after_time, json_out=False)

        changes = utils.compare_graph(before_add, after_add)
        self.assertItemsEqual(changes["added"], ["stack-1", "volume-2",
                                                 "nova-1", "neutron-port-1",
                                                 "nova-2", "neutron-port-2"])

        self.assertEqual(changes["removed"] + changes["removed_edge"] +
                         changes["node_changes"] + changes["edge_changes"], [])
        network_id = '598fd41d-5118-48e5-9b75-862ad070a1e3'
        expected_edges = [("stack-1", "nova-1"), ("stack-1", "nova-2"),
                          ("stack-1", "neutron-port-1"),
                          ("stack-1", "neutron-port-2"),
                          ("stack-1", "volume-2"),
                          ("nova-1", "neutron-port-1"),
                          ("nova-2", "neutron-port-2"),
                          ("nova-1", "volume-2"),
                          ("nova-1", "machine-A"),
                          ("nova-2", "machine-A"),
                          ('neutron-port-1', network_id),
                          ('neutron-port-2', network_id)]
        self.assertItemsEqual(changes["added_edge"], expected_edges)

    def test_nodes_removed(self):
        """
        Test that the removed nodes and connections are correctly removed.
        """
        before_time = self.events["first_delete"] + 60
        after_time = self.events["second_delete"] + 60
        before_delete = self.graph_db.get_graph(before_time, json_out=False)
        after_delete = self.graph_db.get_graph(after_time, json_out=False)

        changes = utils.compare_graph(before_delete, after_delete)

        self.assertEqual(changes["added"] + changes["added_edge"] +
                         changes["node_changes"] + changes["edge_changes"], [])
        expected_removed = ["d1ea0f88-7e65-42fc-864f-915d12d63289",
                            "505c8dc9-12e1-48f3-b738-cb48ed75ae0d",
                            "79e361ac-b875-4520-962f-b49fb1cf4901"]
        self.assertItemsEqual(changes["removed"], expected_removed)

    def test_node_structure(self):
        """
        Tests that nodes are being packed as expected. The first test node is
        normal and the second node contains a renamed attribute.
        """
        node = "96449fb1-0143-4d61-9d84-0a2fd0aa30c1"
        node_structure = {"category": "network", "layer": "virtual",
                          "name": "96449fb1-0143-4d61-9d84-0a2fd0aa30c1",
                          "ip": "10.2.32.169", "mac": "fa:16:3e:7c:5c:66",
                          "type": "vnic"}
        node_2 = "machine-A_eth23_0"
        node_structure_2 = {"category": "network", "layer": "physical",
                            "name": "machine-A_eth23_0", "osdev_type": "2",
                            "allocation": "machine-A", "type": "osdev_network",
                            "address": "54:6a:00:59:d6:33",
                            "osdev_network-name": "eth23"}

        graph = self.graph_db.get_graph(json_out=False)

        self.assertEqual(graph.node[node], node_structure)
        self.assertEqual(graph.node[node_2], node_structure_2)

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
