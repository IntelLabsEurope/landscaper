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
import time
import requests
import networkx as nx
from networkx.readwrite import json_graph

HOST = "localhost"
PORT = 8000

def get_graph():
    """
    Retrieves the entire landscape graph.
    :return: Landscape as a networkx graph.
    """
    landscape = _get("/graph")
    landscape.raise_for_status()  # Raise an exception if we get an error.

    nx_graph = json_graph.node_link_graph(landscape.json())
    return nx_graph


def get_subgraph(node_id, timestamp=None, timeframe=0):
    """
    Grab the subgraph starting from the specified node.
    :param node_id: THe id of the node which will be used to extract the sub.
    :return: A networkx graph of the subgraph. None if the ID is not found.
    """
    timestamp = timestamp or time.time()
    path = "/subgraph/{}".format(node_id)
    subgraph = _get(path, {"timestamp": timestamp, "timeframe": timeframe})

    nx_subgraph = json_graph.node_link_graph(subgraph.json())
    return nx_subgraph


def get_machines(graph):
    """
    Return list of physical machines in the landscape

    :param graph: Networkx graph
    :return: List of physical machines
    """
    machines = {}
    for node, node_data in graph.nodes(data=True):
        if node_data["type"] == "machine":
            machines[node] = node
    return machines


def get_host_machine_for_vm(graph, node_id):
    """
    Return the physical machine that the VM is hosted on.

    :param node_id: Node name
    :return: The host physical machine name
    """
    machine_host = []
    for relation in nx.all_neighbors(graph, node_id):
        if graph.node[relation].get('type') == "machine":
            machine_host.append(relation)
    return machine_host


def get_host_machine_for_stack(graph, node_id):
    """
    Return the physical machine running the software stack

    :param node_id: Node name
    :return: The host physical machine name
    """
    vm_host = []
    machine_host = []
    for relation in nx.all_neighbors(graph, node_id):
        if graph.node[relation].get('type') == "vm":
            vm_host.append(relation)

    for relation in nx.all_neighbors(graph, vm_host[0]):
        if graph.node[relation].get('type') == "machine":
            machine_host.append(relation)
    return machine_host

def get_vm_running_stack(graph, node_id):
    """
    Return the VM that the software stack is running on.

    :param node_id: Node name
    :return: The host physical machine name
    """
    vm_host = []
    for relation in nx.all_neighbors(graph, node_id):
        if graph.node[relation].get('type') == "vm":
            vm_host.append(relation)
    return vm_host


def _get(path, params=None):
    """
    Builds the uri to the service and then retrieves from the host.
    :param path: The path of the service. Host and port are already known.
    :return: A response object of the request.
    """
    uri = "http://{}:{}{}".format(HOST, PORT, path)

    if params:
        uri += "?"
        for param_name, param in params.iteritems():
            if param is None:  # Skip parameters that are none.
                continue
            uri += "{}={}&".format(param_name, param)
        uri = uri[:len(uri)]  # Remove ? or & from the  end of query string
    return requests.get(uri)
