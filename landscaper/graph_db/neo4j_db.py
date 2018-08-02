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
Neo4j Implementation of the graph database.
"""
import json
import time
import logging
import copy

from networkx.readwrite import json_graph
from networkx import DiGraph
from py2neo import Graph, Relationship, Node, NodeSelector, watch

from landscaper.common import EOT_VALUE
from landscaper.common import IDEN_PROPS
from landscaper.common import LOG

from landscaper.graph_db import base

CONFIGURATION_SECTION = 'neo4j'

watch("neo4j.bolt", level=logging.ERROR)
watch("neo4j.http", level=logging.ERROR)


class Neo4jGDB(base.GraphDB):
    """
    Class to persist the landscape to a neo4j database. Nothing is deleted in
    this database. Instead edges between nodes are expired, in this way, we can
    maintain a history of how the landscape has changed over time.
    """
    def __init__(self, conf_manager):
        super(Neo4jGDB, self).__init__(conf_manager)

        # Grab configuration data.
        self.conf_manager = conf_manager
        self.conf_manager.add_section(CONFIGURATION_SECTION)

        # Establish connection to the neo4j DB
        self.connection_timeout = 3600 * 6
        self.graph_db_refreshed = None
        self.graph_db = self._get_db_connection()

    def find(self, label, node_id):
        """
        Returns true or false of whether the node with label exists.
        :param label: node label name.
        :param node_id: Node id.
        :return: Returns true or false of whether the node with label exists.
        """
        node = self.graph_db.find_one(label, property_key="name",
                                      property_value=node_id)
        if node:
            return True
        return False

    def add_node(self, node_id, identity, state, timestmp):
        """
        Add a node to the Neo4j database, which involves adding the identity
        node and also the state node and then creating a relationship between
        them.
        :param node_id: The id of the identity node.
        :param identity: The identity node.
        :param state: State node.
        :param timestmp: Epoch timestamp of when the node was created.
        :return: An instance of the py2neo neo4j node.
        """
        identity = _format_node(identity)
        identity['name'] = node_id
        iden_node = Node(identity.get('category', 'UNDEFINED'), **identity)
        existing_node = self.get_node_by_uuid(node_id)
        if existing_node:
            LOG.warn("Node with UUID: %s already stored in DB", node_id)
            return existing_node

        # Store nodes to the database.
        transaction = self.graph_db.begin()
        state = _format_node(state)
        state_label = identity.get('category', 'UNDEFINED') + '_state'
        state_node = Node(state_label, **state)
        state_rel = self._create_edge(iden_node, state_node, timestmp, "STATE")
        transaction.create(iden_node)
        transaction.create(state_node)
        transaction.create(state_rel)
        transaction.commit()

        return iden_node

    def update_node(self, node_id, timestamp, state=None, extra_attrs=None):
        """
        Updating a node in the database involves expiring the old state node
        and then creating a new state node and linking it to identity node
        which is being updated.
        :param additional_attributes:
        :param node_id: The identity node id.
        :param state:  The new state.
        :param timestamp: Epoch timestamp of when the update occurred.
        :return:  Instance of the identity node.
        """
        state_attrs = None
        identity = self.get_node_by_uuid(node_id)

        if not identity:
            umsg = "Node: %s. Node not in the landscape." % node_id
            LOG.warn(umsg)
            return (None, umsg)

        if not state and not extra_attrs:
            umsg = "Node: %s. No attributes supplied for update." % node_id
            LOG.warn(umsg)
            return (identity, umsg)

        if state:
            state_attrs = state

        old_state = self._get_state_node(identity, time.time())
        if not old_state:
            umsg = "Can't update node: %s, as it is already expired." % node_id
            LOG.warn(umsg)
            return (identity, umsg)

        old_node, old_edge = old_state

        if extra_attrs:
            if state_attrs:
                state_attrs.update(extra_attrs)
            else:
                state_attrs = dict(old_node)
                state_attrs.update(extra_attrs)

        if state_attrs == dict(old_node):
            umsg = "Node: %s. No update. Current state is identical" % node_id
            LOG.warn(umsg)
            return (identity, umsg)

        # Create new state and edge to identity.
        state_label = identity.get('category', 'UNDEFINED') + '_state'
        state_node = Node(state_label, **state_attrs)
        new_edge = self._create_edge(identity, state_node, timestamp, 'STATE')

        # Expire old edge between identity and state.
        self._expire_edge(old_edge, timestamp)

        # Commit it all
        self.graph_db.push(old_edge)
        transaction = self.graph_db.begin()
        transaction.create(new_edge)
        transaction.commit()

        umsg = "Node %s updated successfully" % node_id
        return (identity, umsg)

    def add_edge(self, src_node, dest_node, timestamp, label=None):
        """
        Add an edge between two nodes and attach timestamp details as an
        attribute, which details when the pointed to node was created, updated
        or deleted.
        :param src_node: The source node.
        :param dest_node: The destination node.
        :param timestamp: The epoch timestamp of when this edge was created.
        :param label: Description of the edge.
        :return: Instance of an edge.
        """
        # Add link between src and dst nodes.
        edge = self._create_edge(src_node, dest_node, timestamp, label)

        if edge is not None and self.graph_db.exists(edge):
            LOG.warn("Trying to add a relation already stored in the DB")
            return edge
        transaction = self.graph_db.begin()
        transaction.create(edge)
        transaction.commit()
        return edge

    def update_edge(self, src_node, dest_node, timestamp, label=None):
        """
        Updates and edges timestamp attributes by expiring the old edge and
        adding a new edge. The new edge will then highlight the time of an
        update.
        :param src_node: Source Node.
        :param dest_node: Destination Node.
        :param timestamp: Epoch timestamp for when the update occurred.
        :param label: Edge Description.
        :return: Edge instance.
        """
        # Remove old edge
        self.delete_edge(src_node, dest_node, timestamp, label)

        # Create new edge
        edge = self._create_edge(src_node, dest_node, timestamp, label)
        transaction = self.graph_db.begin()
        transaction.create(edge)
        transaction.commit()
        return edge

    def delete_edge(self, src_node, dest_node, timestamp, label=None):
        """
        Deletes an edge by expiring its 'to' attribute.
        :param src_node: Source Node
        :param dest_node: Destination Node
        :param timestamp: epoch timestamp of when the edge was deleted.
        :param label: Description of the edge.
        :return: Instance of deleted edge.
        """
        # Add link between src and dst nodes.
        edge = self._get_edge(src_node, dest_node, timestamp, label)

        if edge is not None and self.graph_db.exists(edge):
            self._expire_edge(edge, timestamp)
            self.graph_db.push(edge)
            return edge
        return None

    def delete_node(self, identity, timestamp):
        """
        A node is effectively deleted by expiring all inward and outward edges.
        :param identity: Node to delete.
        :param timestamp:  epoch timestamp of when it was deleted.
        """
        successors = self._get_successors(identity, timestamp=timestamp)
        for _, successor_edge in successors:
            self._expire_edge(successor_edge, timestamp)
            self.graph_db.push(successor_edge)

        predecessors = self._get_predecessors(identity, timestamp=timestamp)
        for _, predecessor_edge in predecessors:
            self._expire_edge(predecessor_edge, timestamp)
            self.graph_db.push(predecessor_edge)

    def predecessors(self, node):
        """
        List of nodes which precede the given node.
        :param node: Reference node
        :return: List of nodes which precede the given node.
        """
        return self._get_predecessors(node)

    def successors(self, node):
        """
        List of nodes which succeed the given node.
        :param node: Reference node
        :return: List of nodes which succeed the given node.
        """
        return self._get_successors(node)

    def get_node_by_properties_web(self, properties, start=None, timeframe=0):
        """
        Return a list of nodes which match the given properties.
        :param properties: A tuple with the key, value.  Example: (k, v)
        :return: A graph of matching nodes
        """
        start = start or time.time()
        if not properties:
            return None
        start = int(float(start))
        timeframe = int(float(timeframe))
        end = start + timeframe
        # Build conditional query
        conditional_query = ""
        property_key = properties[0]
        property_value = properties[1]
        propery_operator = "="
        condition = '(n.{0}{1}"{2}" OR s.{0}{1}"{2}")'.format(property_key,
                                                              propery_operator,
                                                              property_value)
        conditional_query += condition
        query = 'match (n)-[r:STATE]->(s) where {0} ' \
                'AND (r.from <= {1} AND r.to > {2}) return n, s'\
            .format(conditional_query, start, end)
        graph = DiGraph()
        for id_node, state_node in self.graph_db.run(query):
            node = dict(id_node)
            state_attributes = self._unique_attribute_names(IDEN_PROPS,
                                                            dict(state_node),
                                                            node["type"])
            node.update(state_attributes)
            graph.add_node(node["name"], node)
        graph_json = json.dumps(json_graph.node_link_data(graph))
        return graph_json

    def get_nodes_by_properties(self, properties):
        """
        :param properties: Dictionary of properties, keys and values.
        :return:  List of node instances.
        """
        conditions = list()
        for key in properties.keys():
            conditions.append('_.{} = "{}"'.format(key, properties[key]))
        selector = NodeSelector(self.graph_db)
        selected = selector.select().where(*conditions)
        return list(selected)

    def get_node_by_uuid_web(self, uuid, json_out=True):
        """
        Returns a networkx graph containing matching node.
        :param uuid: The node name.
        :return: Graph containing node or none.
        """
        graph = DiGraph()
        node_query = "match (i)-[r:STATE]->(s) where i.name='{}' and r.to>{}" \
                     " return i, s".format(uuid, str(time.time()))
        query_result = self.graph_db.run(node_query)

        result = list(query_result)
        if result:
            records = result[0]
            node = dict(records[0])
            state_attrs = dict(records[1])
            if 'geo' in state_attrs:
                state_attrs['geo'] = json.loads(state_attrs['geo'])

            state_attributes = self._unique_attribute_names(IDEN_PROPS,
                                                            state_attrs,
                                                            node["type"])
            node.update(state_attributes)
            graph.add_node(uuid, node)

            if json_out:
                graph = json.dumps(json_graph.node_link_data(graph))
            return graph
        return None

    def get_node_by_uuid(self, node_id):
        """
        Retrieve a node from the neo4j database.
        :param node_id: THe node to retrieve.
        :return: The node
        """
        selector = NodeSelector(self.graph_db)
        selected = list(selector.select().where('_.name="{}"'.format(node_id)))
        if selected:
            return selected[0]
        return None

    def delete_all(self):
        """
        Delete all nodes and edges from the database.
        """
        self.graph_db.delete_all()

    def _get_edge(self, src_node, dest_node, timestamp, label=None):
        """
        Returns first edge which has not expired.
        :param src_node: Source Node.
        :param dest_node: Destination Node.
        :param timestamp: Edge must hae been alive at this time.
        :param label: Edge Description.
        :return: Edge instance.
        """
        timestamp = round(float(timestamp), 2)
        edges = self.graph_db.match(src_node, label, dest_node)
        for edge in edges:
            edge_from = round(float(edge['from']), 2)
            edge_to = float(edge['to'])
            if edge_from <= timestamp and edge_to == EOT_VALUE:
                return edge
        return None

    @staticmethod
    def _create_edge(source_node, destination_node, timestamp, label):
        """
        Creates a directed edge from the source node to the destination node.
        :param source_node: Source Node.
        :param destination_node: Destination Node.
        :param timestamp: Time of source node creation.
        :param label: Edge description.
        :return: Returns newly created edge.
        """
        edge = Relationship(source_node, label, destination_node)
        edge["from"] = int(timestamp)
        edge["to"] = int(EOT_VALUE)
        return edge

    @staticmethod
    def _expire_edge(edge, timestamp):
        """
        Expires the relationship. This effectively deletes the node which this
        relationship was pointing to.
        :param edge: Relationship to expire.
        :param timestamp: Time at which the edge was expired.
        :return: The expired edge.
        """
        edge['to'] = int(timestamp)
        return edge

    def _get_state_node(self, identity_node, timestamp):
        """
        Return the latest living state.
        :param identity_node: The identity node which the state is attached to.
        :param timestamp: Time at which the state should have been alive.
        :return: The latest, living state node.
        """
        states = self._get_successors(identity_node, 'STATE', timestamp)
        if states:
            return states[0]
        return None

    def _existing_relation(self, src_node, dst_node, timestamp, label=None):
        end_nodes = self._get_successors(src_node, label=label,
                                         timestamp=timestamp)
        for end_node, relation in end_nodes:
            dst_uuid = dst_node.dict().get('name', 'dst_uuid')
            end_uuid = end_node.dict().get('name', 'end_uuid')
            if dst_uuid == end_uuid:
                return relation
        return None

    def _get_successors(self, identity_node, label=None, timestamp=None):
        """
        Get a list of successors to a node. If no timestamp is provided then
        all successors are returned.

        :param identity_node: Start node.
        :param label: Only return successors with this type of relationship.
        :param timestamp: epoch timestamp. If used will only find living nodes.
        :return List: List of successors.
        """
        timestamp = round(float(timestamp), 2) if timestamp else timestamp
        results = []
        for edge in self.graph_db.match(identity_node, label):
            if timestamp:
                edge_from = round(float(edge['from']), 2)
                edge_to = float(edge['to'])

                # edge existed at timestamp and edge still alive.
                if edge_from <= timestamp and edge_to == EOT_VALUE:
                    edge_end_node = edge.end_node()
                    results.append((edge_end_node, edge))
            else:
                edge_end_node = edge.end_node()
                results.append((edge_end_node, edge))

        return results

    def _get_predecessors(self, identity_node, label=None, timestamp=None):
        """
        Get a list of predecessors to a node. If no timestamp is provided then
        all predecessors are returned.

        :param identity_node: End node.
        :param label: Only return predecessors with this type of relationship.
        :param timestamp: epoch timestamp. If used will only find living nodes.
        :return List: List of predecessors and their edges.
        """
        results = []
        timestamp = round(float(timestamp), 2) if timestamp else timestamp
        edges_in = self.graph_db.match(end_node=identity_node, rel_type=label)
        for edge in edges_in:
            if timestamp:
                edge_from = round(float(edge['from']), 2)
                edge_to = float(edge['to'])

                # edge existed at timestamp and edge still alive.
                if edge_from <= timestamp and edge_to == EOT_VALUE:
                    edge_start_node = edge.start_node()
                    results.append((edge_start_node, edge))
            else:
                edge_start_node = edge.start_node()
                results.append((edge_start_node, edge))

        return results

    def get_subgraph(self, node_id, timestmp=None, timeframe=0, json_out=True):
        timestmp = timestmp or time.time()

        result = DiGraph()
        endtime = int(float(timestmp)) + int(float(timeframe))

        tmp = 'MATCH (n)-[rels*]->(m) ' \
              'WHERE n.name="{0}" AND ALL ' \
              '(rel in rels WHERE rel.from <= {1} AND rel.to >= {2} ) ' \
              'RETURN DISTINCT n, rels, m' \
              ''.format(node_id, str(timestmp), str(endtime))

        LOG.info(tmp)
        query_result = self.graph_db.run(tmp)

        first = True
        relations = list()

        for record in query_result:
            if first:
                nodes_index = [0, 2]
                first = False
            else:
                nodes_index = [2]

            for i in nodes_index:
                labels = list(record[i].labels())
                if labels:
                    label = labels[0]
                else:
                    label = 'state'

                if 'state' not in label:
                    tmp = dict(record[i])
                    node_id = tmp.get('name', None)
                    result.add_node(node_id, tmp)

            for relation in record[1]:
                if relation.type() == 'STATE':
                    node_id = dict(relation.start_node()).get('name', None)
                    if node_id is not None:
                        if node_id in result.node:
                            prefix = result.node[node_id]["type"]
                        else:
                            prefix = "component"
                        state = dict(relation.end_node())
                        if 'geo' in state:
                            state['geo'] = json.loads(state['geo'])

                        state_attrs = self._unique_attribute_names(IDEN_PROPS,
                                                                   state,
                                                                   prefix)
                        result.add_node(node_id, state_attrs)
                else:
                    relations.append(relation)

        for rel in relations:
            src_uuid = dict(rel.start_node()).get('name', 'None')
            dst_uuid = dict(rel.end_node()).get('name', 'None')
            if result.has_node(src_uuid) and result.has_node(dst_uuid):
                label = rel.type()
                rel_attr = dict(rel)
                result.add_edge(src_uuid, dst_uuid, rel_attr, label=label)

        if result.node:
            if json_out:
                js_gr = json_graph.node_link_data(result)
                result = json.dumps(js_gr)
            return result
        return None

    def get_graph(self, timestamp=None, timeframe=0, json_out=True):
        if timestamp is None:
            timestamp = time.time()

        endtime = timestamp + timeframe

        result = DiGraph()

        tmp = 'MATCH (idnode)-[rs:STATE]->(statenode) WHERE (rs.from <= {0} ' \
              'AND rs.to > {1}) ' \
              'RETURN idnode, statenode;'.format(str(timestamp), str(endtime))

        for idnode, statenode in self.graph_db.run(tmp):
            uuid = dict(idnode).get('name', None)
            if uuid is not None:
                attr = dict(idnode)
                state_attrs = dict(statenode)
                if 'geo' in state_attrs:
                    state_attrs['geo'] = json.loads(state_attrs['geo'])
                state_attributes = self._unique_attribute_names(IDEN_PROPS,
                                                                state_attrs,
                                                                attr["type"])
                attr.update(state_attributes)
                result.add_node(uuid, attr)

        all_edges = "match ()-[r]-() where type(r) <> 'STATE' and r.from <= " \
                    "{0} and r.to > {1} return r".format(str(timestamp),
                                                         str(endtime))
        for edge in self.graph_db.run(all_edges):
            rel_attr = dict(edge[0])
            src_uuid = edge[0].start_node()["name"]
            dst_uuid = edge[0].end_node()["name"]
            result.add_edge(src_uuid, dst_uuid, rel_attr, label=edge[0].type())

        if json_out:
            js_gr = json_graph.node_link_data(result)
            result = json.dumps(js_gr)

        return result

    def __getattribute__(self, item):
        if item == "graph_db" and self._connection_elapsed():
            LOG.info("Refreshing connection.")
            return self._get_db_connection()
        return object.__getattribute__(self, item)

    def _connection_elapsed(self):
        """
        Returns true if the connection to the database has reached the timeout
        set in the constructor.
        :return: True if the connection timed out.
        """
        elapsed_time = time.time() - self.graph_db_refreshed
        if elapsed_time > self.connection_timeout:
            return True
        return False

    def _get_db_connection(self):
        """
        Returns a connection to the NEO4J Database.
        :return:  A connection to the NEO4J Database.
        """
        url = self.conf_manager.get_neo4j_url()
        user, password, use_bolt = self.conf_manager.get_neo4j_credentials()
        self.graph_db_refreshed = time.time()
        return Graph(url, user=user, password=password, bolt=use_bolt)

    def _unique_attribute_names(self, immutable_keys, attributes, prefix):
        """
        Ensures that the attributes do not contain the same keys as an key in
        the immutable key list.
        :param immutable_keys: List of keys that cannot be in attributes.
        :param attributes: Dictionary of attributes.
        :param prefix: Prefix for any key in attributes that clashes with the
        immutable_keys.
        :return: Attributes which are modified if they are clashing with
        immutable_keys.
        """
        attrs = copy.deepcopy(attributes)
        matching_keys = set(immutable_keys).intersection(set(attrs))
        for key in matching_keys:
            unique_key = self._unique_key(key, attrs.keys(), prefix)
            attrs[unique_key] = attrs.pop(key)
        return attrs

    @staticmethod
    def _unique_key(clashing_key, keys, prefix):
        """
        Returns a unique key from those already in keys.
        :param clashing_key: THe key to rename.
        :param keys: list of keys that the clashing key must be unique against.
        :param prefix: prefix for the clashing key.
        :return: Unique Key
        :raise: AttributeError if a unique key cannot be generated.
        """
        base_key = "{}-{}".format(prefix, clashing_key)
        if base_key not in keys:
            return base_key

        for i in range(1, 100):
            unique_key = "{}_{}".format(base_key, i)
            if unique_key not in keys:
                return unique_key

        raise AttributeError("Unable to create unique attribute key")

    def load_test_landscape(self, graph_file):
        """
        Loads the test graph into the database, for integration tests.
        :param graph: Networkx Test Graph.
        """
        graph_data = json.load(open(graph_file))
        graph = json_graph.node_link_graph(graph_data, directed=True)

        node_lookup = {}
        for node_id, node_data in graph.nodes(data=True):
            node_attrs = _format_node(node_data)
            if "_state_" in node_id:
                category = node_id.split("_")[0] + "_state"
            else:
                category = node_attrs["category"]
            node = Node(category, **node_attrs)
            node_lookup[node_id] = node

        rels = []
        for src, dest, edge_attrs in graph.edges(data=True):
            label = edge_attrs["label"]
            del edge_attrs["label"]
            src_node = node_lookup[src]
            dest_node = node_lookup[dest]
            rel = Relationship(src_node, label, dest_node, **edge_attrs)
            rels.append(rel)

        transaction = self.graph_db.begin()
        for _, node_object in node_lookup.iteritems():
            transaction.create(node_object)
        for rel_object in rels:
            transaction.create(rel_object)
        transaction.commit()


def _format_node(node):
    """
    Prepares a node for insertion into the graph database. Dictionaries cannot
    be inserted.
    :param node: Node to format.
    :return: Formatted node.
    """
    formatted_node = dict()
    for prop in node:
        if isinstance(node[prop], dict) or isinstance(node[prop], list):
            formatted_node[prop] = json.dumps(node[prop])
        else:
            formatted_node[prop] = node[prop]
    return formatted_node


def _attributes_equal(new_attributes, old_attributes):
    """
    Compare attributes (dict) by value to determine if a state is changed

    :param new_attributes: dict containing attributes
    :param old_attributes: dict containing attributes
    :return bool: result of the comparison between new_attributes and
    old attributes
    """
    for key in new_attributes:
        if key not in old_attributes:
            return False
        elif new_attributes[key] != old_attributes[key]:
            return False
    return True
