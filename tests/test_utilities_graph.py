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
Tests for the utilities.graph module.
"""
import json
import unittest

import networkx as nx
from networkx.readwrite import json_graph

from landscaper.utilities import graph as graph_utils


class TestFilterNodes(unittest.TestCase):
    """
    Tests against the filter nodes method.
    """
    def setUp(self):
        self.types = ['machine', 'vm', 'stack']

    def test_graph_a_inverse_filtering(self):
        """
        Test against sample graph A.
        """
        graph = sample_graphs('sample-a')
        filtered_graph = graph_utils.filter_nodes(graph, self.types,
                                                  filter_these=False,
                                                  json_out=False)

        self.assertItemsEqual(filtered_graph.node, ['A', 'R', 'F'])
        self.assertEqual(filtered_graph.successors('A'), ['F'])
        self.assertEqual(filtered_graph.successors('R'), ['F'])
        self.assertEqual(filtered_graph.successors('F'), [])

    def test_graph_b_inverse_filtering(self):
        """
        Test against sample graph B.
        """
        graph = sample_graphs('sample-b')
        filt_graph = graph_utils.filter_nodes(graph, self.types,
                                              filter_these=False,
                                              json_out=False)

        self.assertItemsEqual(filt_graph.node, ['B', 'C', 'D', 'E', 'F', 'I'])
        self.assertItemsEqual(filt_graph.successors('B'), ['C', 'D', 'E'])
        self.assertItemsEqual(filt_graph.successors('C'), [])
        self.assertItemsEqual(filt_graph.successors('D'), ['F'])
        self.assertItemsEqual(filt_graph.successors('E'), ['F'])
        self.assertItemsEqual(filt_graph.successors('F'), [])

    def test_graph_c_inverse_filtering(self):
        """
        Test against sample graph C.
        """
        graph_c = sample_graphs('sample-c')
        filt_graph = graph_utils.filter_nodes(graph_c, self.types,
                                              filter_these=False,
                                              json_out=False)

        self.assertItemsEqual(filt_graph.node, ['A', 'D', 'E', 'G'])
        self.assertItemsEqual(filt_graph.successors('A'), ['D', 'E'])
        self.assertItemsEqual(filt_graph.successors('D'), ['E', 'G'])
        self.assertItemsEqual(filt_graph.successors('E'), ['G'])
        self.assertItemsEqual(filt_graph.successors('G'), [])

    def test_graph_a_filtering(self):
        """
        Filter types out for graph A.
        """
        graph_a = sample_graphs('sample-a')
        filt_graph = graph_utils.filter_nodes(graph_a, self.types,
                                              filter_these=True,
                                              json_out=False)

        self.assertItemsEqual(filt_graph.node, ['B', 'C', 'D', 'E'])
        self.assertItemsEqual(filt_graph.successors('B'), [])
        self.assertItemsEqual(filt_graph.successors('C'), [])
        self.assertItemsEqual(filt_graph.successors('D'), ['E'])
        self.assertItemsEqual(filt_graph.successors('E'), [])

    def test_graph_b_filtering(self):
        """
        Filter types out for graph B.
        """
        graph_b = sample_graphs('sample-b')
        filt_graph = graph_utils.filter_nodes(graph_b, self.types,
                                              filter_these=True,
                                              json_out=False)

        self.assertItemsEqual(filt_graph.node, ['A', 'H', 'G'])
        self.assertItemsEqual(filt_graph.successors('A'), ['G', 'H'])
        self.assertItemsEqual(filt_graph.successors('G'), [])
        self.assertItemsEqual(filt_graph.successors('H'), ['G'])

    def test_graph_c_filtering(self):
        """
        Filter types out for graph C.
        """
        graph_c = sample_graphs('sample-c')
        filt_graph = graph_utils.filter_nodes(graph_c, self.types,
                                              filter_these=True,
                                              json_out=False)

        self.assertItemsEqual(filt_graph.node, ['B', 'C', 'F'])
        self.assertItemsEqual(filt_graph.successors('B'), ['F'])
        self.assertItemsEqual(filt_graph.successors('C'), ['F'])
        self.assertItemsEqual(filt_graph.successors('F'), [])

    def test_json_out_false(self):
        """
        Test that json out parameter works, true.
        """
        graph = sample_graphs('sample-a')
        filter_g = graph_utils.filter_nodes(graph, [], filter_these=True,
                                            json_out=False)
        self.assertIsInstance(filter_g, nx.DiGraph)

    def test_json_out_true(self):
        """
        Test that json out parameter works, false.
        """
        graph = sample_graphs('sample-a')
        filter_g = graph_utils.filter_nodes(graph, [], filter_these=True,
                                            json_out=True)
        filter_o = json_graph.node_link_graph(json.loads(filter_g),
                                              directed=True)
        self.assertIsInstance(filter_g, basestring)
        self.assertIsInstance(filter_o, nx.DiGraph)

    def test_json_graph_passed(self):
        """
        filter_nodes can take a networkx graph as a string.
        """
        graph = sample_graphs('sample-a')
        j_graph = json.dumps(json_graph.node_link_data(graph))

        filter_graph = graph_utils.filter_nodes(j_graph, [], filter_these=True,
                                                json_out=False)
        self.assertIsInstance(filter_graph, nx.DiGraph)


def sample_graphs(graph_id):
    """
    Sample graphs. The positive and negfative filtering is known for all of
    the sample graphs.
    :param graph_id: sample graph id.
    :return: sample graph as a networkx object.
    """
    grap = None
    if graph_id == "sample-a":
        grap = {'directed': True, 'graph': {},
                'nodes': [{'type': 'stack', 'id': 'A'},
                          {'type': 'v', 'id': 'C'}, {'type': '<c>', 'id': 'B'},
                          {'type': '1', 'id': 'E'}, {'type': '[q]', 'id': 'D'},
                          {'type': 'vm', 'id': 'F'},
                          {'type': 'stack', 'id': 'R'}],
                'links': [{'source': 0, 'target': 1},
                          {'source': 0, 'target': 2},
                          {'source': 0, 'target': 4},
                          {'source': 3, 'target': 5},
                          {'source': 4, 'target': 3},
                          {'source': 6, 'target': 4}], 'multigraph': False}
    elif graph_id == "sample-b":
        grap = {'directed': True, 'graph': {},
                'nodes': [{'type': '', 'id': 'A'}, {'type': 'vm', 'id': 'C'},
                          {'type': 'stack', 'id': 'B'},
                          {'type': 'vm', 'id': 'E'},
                          {'type': 'machine', 'id': 'D'},
                          {'type': '', 'id': 'G'}, {'type': 'vm', 'id': 'F'},
                          {'type': 'stack', 'id': 'I'},
                          {'type': 'k', 'id': 'H'}],
                'links': [{'source': 0, 'target': 8},
                          {'source': 0, 'target': 2},
                          {'source': 2, 'target': 1},
                          {'source': 2, 'target': 3},
                          {'source': 2, 'target': 4},
                          {'source': 3, 'target': 6},
                          {'source': 4, 'target': 6},
                          {'source': 6, 'target': 5},
                          {'source': 7, 'target': 5},
                          {'source': 8, 'target': 7}], 'multigraph': False}
    elif graph_id == "sample-c":
        grap = {'directed': True, 'graph': {},
                'nodes': [{'type': 'stack', 'id': 'A'},
                          {'type': '', 'id': 'C'}, {'type': '', 'id': 'B'},
                          {'type': 'vm', 'id': 'E'}, {'type': 'vm', 'id': 'D'},
                          {'type': 'vm', 'id': 'G'}, {'type': '', 'id': 'F'}],
                'links': [{'source': 0, 'target': 1},
                          {'source': 0, 'target': 2},
                          {'source': 1, 'target': 3},
                          {'source': 1, 'target': 4},
                          {'source': 2, 'target': 4},
                          {'source': 3, 'target': 5},
                          {'source': 4, 'target': 3},
                          {'source': 4, 'target': 6},
                          {'source': 6, 'target': 5}], 'multigraph': False}
    if grap:
        return json_graph.node_link_graph(grap, directed=True)
    return None
