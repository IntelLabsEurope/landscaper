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
Landscape database base class.
"""
import abc
import os


class GraphDB(object):
    """
    Base class for a graph database.  The graph database is responsible for
    interfacing with the databaase in which the landscape will be stored.
    """

    def __init__(self, conf_manager):
        pass

    @abc.abstractmethod
    def add_node(self, node_id, identity, state, timestmp):
        """
        Adds an identity node to the landscape and attaches the current state
        to the identity node. The edge between the nodes will have a from
        and to attributes defining when the identity node was last in this
        state.
        :param node_id: The id of the identity node.
        :param identity: The node to add to the landscape.
        :param state: Node which shows the current state of the identity node.
        :param timestamp: Time of when the node was created.
        :return: Returns the identity node as a landscape object.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def add_edge(self, src_node, dest_node, timestamp, label=None):
        """
        Adds an edge from the src_node to the dest_node.  Timestamp is added
        to the edge as a 'from' attribute, 'to' is also added as an attribute
        and is expired when the edge is deleted.
        :param src_node: Source Node.
        :param dest_node: Destination Node.
        :param timestamp: Epoch timestamp of when the edge was created.
        :param label: Description of the relationship, such as 'RESIDES_ON'.
        :return: Instance of the newly created edge.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_node(self, node_id, identity, state, timestmp):
        """
        Updates the identity node by adding a new state node and expiring the
        previous state
        :param node_id: ID for the identity node.
        :param identity: The node to update.
        :param state: The new state of the node.
        :param timestmp: Epoch timestamp of when the modification occurred.
        :return: Instance of newly created node.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_edge(self, src_node, dest_node, timestamp, label=None):
        """
        Updates the edge by creating a new edge and expiring the old one.
        :param src_node: Source Node.
        :param dest_node: Destination Node.
        :param timestamp: epoch timestamp.
        :param label: Description of the relationship, such as 'RESIDES_ON'.
        :return: Instance of the newly created edge.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_edge(self, src_node, dest_node, timestamp, label=None):
        """
        Deletes an edge by expiring the 'to' attribute. This involves setting
        the 'to' variable to the timestamp.
        :param src_node: Source Node.
        :param dest_node: Destination Node.
        :param timestamp: epoch timestamp of the time the edge was deleted.
        :param label: Description of the relationship, such as 'RESIDES_ON'.
        :return: Instance of the deleted edge.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_node(self, identity, timestamp):
        """
        Deletes the node from the landscape.
        :param identity: Instance of the node to delete.
        :param timestamp: Epoch timestamp of when the node will be deleted.
        :return: Instance of the deleted node.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_nodes_by_properties(self, properties):
        """
        Retrieves a list of nodes matching the properties supplied.
        :param properties: Properties to query against.
        :return: Nodes matching the properties.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_node_by_uuid(self, node_id):
        """
        Fetches a node by it's id.
        :param node_id: Id of the node.
        :return: An instance of the node.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_all(self):
        """
        Deletes all nodes and relationships in the landscape.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_graph(self, timestamp=None, timeframe=0, json_out=True):
        """
        Returns the entire landscape graph, with all nodes and edges.
        :param timestamp:  Query only nodes that were alive at this time.
        :param timeframe: And that were still alive at this time.
        :return: The landscape graph.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_subgraph(self, node_id, timestmp=None, timeframe=0, json_out=True):
        """
        Returns a subgraph from the landscape, related to the given node.
        :param node_id: Id of the node.
        :param timestamp: Query only nodes that were alive at this time.
        :param timeframe: Query nodes that were alive from timestamp and for
        the duration of timeframe.
        :return: Landscape subgraph.
        """
        raise NotImplementedError

    @staticmethod
    def get_installation_dir():
        """
        Get the installation directory for a graph database.
        :return: Installation directory.
        """
        return os.path.dirname(os.path.abspath(__file__))
