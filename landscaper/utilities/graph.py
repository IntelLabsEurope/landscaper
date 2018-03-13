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
Functions related to networkx graph manipulation.
"""
import json
import operator
import networkx as nx
from networkx.readwrite import json_graph


def filter_nodes(graph, types, filter_these=True, json_out=True):
    """
    Filters the node types from a graph and connects the nodes as appropriate.
    The types that are filtered are decided by the types and filter_these
    parameters.  If filter_these is set to true then filter out the node types
    in the types list, if false, then filter out the other node types.
    :param graph: The graph to filter.
    :param types: The types to keep or filter from the graph.
    :param filter_these: Flag which decides whether types are filtered or kept.
    :param json_out: If true then json is returned rather than a graph.
    :return: A networkx graph as an object or as json.
    """
    graph = _graph_obj(graph)
    filter_operator = operator.not_ if filter_these else operator.truth
    new_graph = nx.DiGraph()
    end_nodes = _end_nodes(graph)
    for end_node in end_nodes:
        _filter_types(graph, new_graph, end_node, None, types, filter_operator)
    if json_out:
        return json.dumps(json_graph.node_link_data(new_graph))
    return new_graph


def _filter_types(graph, new_graph, nid, source, types, filter_operator):
    """
    Recursive method which walks, depth first, through the graph. Nodes are
    checked by their type and added if required to the new_graph.
    :param graph: graph that is being traversed through.
    :param new_graph: graph being built.
    :param nid: current node being inspected.
    :param source: last node that was added.
    :param types: list of types that are being checked against.
    :param filter_operator: comparison operator.
    :return: None
    """
    ntype = graph.node[nid]['type']
    if filter_operator(operator.contains(types, ntype)):
        new_graph.add_node(nid, **graph.node[nid])
        if source:
            new_graph.add_edge(source, nid)
        source = nid
    successors = graph.successors(nid)
    for succ in successors:
        _filter_types(graph, new_graph, succ, source, types, filter_operator)
    return


def _end_nodes(graph):
    """
    Returns all nodes with no predecessors. We filter the graph form these
    nodes.
    """
    end_nodes = []
    for node in graph:
        predecessor = graph.predecessors(node)
        if not predecessor:
            end_nodes.append(node)
    return end_nodes


def _graph_obj(graph):
    """
    converts json strings to graph objects.
    """
    if isinstance(graph, basestring):
        json_g = json.loads(graph)
        return json_graph.node_link_graph(json_g, directed=True)
    return graph
