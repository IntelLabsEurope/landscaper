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
Utilities used for testing.
"""
import collections
import ConfigParser
import random
import string
import os

EdgeChange = collections.namedtuple('EdgeChange', 'edge original changed')
NodeChange = collections.namedtuple('NodeChange', 'node original changed')

TEST_CONFIG_FILE = "tests/data/tmp_config.conf"


def compare_graph(first, second):
    """
    Compares the second graph to the first graph and returns the changes in the
    second graph.
    :param first: A networkx (sub)graph.
    :param before: A networkx (sub)graph.
    :returns A dict with changes.
    """
    changes = {'added': [],
               'removed': [],
               'added_edge': [],
               'removed_edge': [],
               'node_changes': [],
               'edge_changes': []}
    for node in second.nodes():
        if node not in first.nodes():
            # add missing nodes
            if node not in changes['added']:
                changes['added'].append(node)
            for edge in second.out_edges([node]):
                src = edge[1]
                if src not in first.nodes() and src not in changes['added']:
                    changes['added'].append(src)
                changes['added_edge'].append(edge)
        else:
            if first.node[node] != second.node[node]:
                changes['node_changes'].append((node, first.node[node],
                                                second.node[node]))
    for node in first.nodes():
        if node not in second.nodes():
            changes['removed'].append(node)
            for edge in first.out_edges([node]):
                changes['removed_edge'].append(edge)
        else:
            # node exists lets check the edges.
            for edge_data in second.out_edges([node], data=True):
                edge = edge_data[0:2]
                if edge not in first.out_edges([node]):
                    changes['added_edge'].append(edge)
                else:
                    changed_attrs = edge_data[2]
                    orig_attrs = _find_matching_edge(edge, first)[2]
                    if orig_attrs != changed_attrs:
                        change = EdgeChange(edge, orig_attrs, changed_attrs)
                        changes['edge_changes'].append(change)

            for edge in first.out_edges([node]):
                if edge not in second.out_edges([node]):
                    changes['removed_edge'].append(edge)
    return changes


def _find_matching_edge(edge, graph):
    """
    Retrieve an edge matching the edge inserted from the graph.
    :param edge: The edge to find.
    :param graph: The graph to find it in.
    :return: The edge including attributes.
    """
    edges_data = graph.out_edges([edge[0]], data=True)
    edges = [edge_data[0:2] for edge_data in edges_data]
    matching_edge_index = edges.index(edge)
    return edges_data[matching_edge_index]


def write_config(config_params, config_file):
    """
    Creates a test configuration for testing.
    """
    cfgfile = open(config_file, 'w+')
    config = ConfigParser.ConfigParser()
    for section, attributes in config_params.iteritems():
        config.add_section(section)
        for attribute_k, attribute_v in attributes.iteritems():
            config.set(section, attribute_k, attribute_v)
    config.write(cfgfile)
    cfgfile.close()


def create_test_config():
    """"
    Creates a sample test configuration used for testing and writes this
    to the testing data directory.
    """
    gdb_env = "USE_TEST_GDB"
    if gdb_env not in os.environ:
        msg = "Set '{}' to true, to run these tests".format(gdb_env)
        raise AttributeError(msg)
    if os.environ[gdb_env].lower() != "true":
        msg = "Functionality for setting {} to false not ready".format(gdb_env)
        raise AttributeError(msg)

    user_env = "NEO4J_USER"
    pass_env = "NEO4J_PASS"

    if user_env not in os.environ or pass_env not in os.environ:
        err = "{} and {} needed for the test neo4j database.".format(user_env,
                                                                     pass_env)
        raise AttributeError(err)

    username = os.environ[user_env]
    password = os.environ[pass_env]
    test_config = {"neo4j": {"url": "http://localhost:7474/db/data",
                             "user": username, "password": password},
                   "general": {"graph_db": "Neo4jGDB",
                               "event_listeners": "", "collectors": ""},
                   "physical_layer": {"machines": "machine-A"}}

    # Add RabbitMQ listener configs
    test_config['rabbitmq'] = {}
    conf_vars = ['rb_name', 'rb_password', 'rb_host', 'rb_port', 'topic',
                 'notification_queue', 'exchanges']
    for conf_var in conf_vars:
        test_config['rabbitmq'][conf_var] = random_string(8)

    write_config(test_config, TEST_CONFIG_FILE)


def remove_test_config():
    """
    Remove the test configuration from the data directory.
    """
    if os.path.isfile(TEST_CONFIG_FILE):
        os.remove(TEST_CONFIG_FILE)


def random_string(length):
    """
    Generate a random string.
    :param length: Length of the random string
    """
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))
