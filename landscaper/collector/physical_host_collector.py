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
Physical layer collector.
"""
import os
import time
import xml.etree.ElementTree as Et
from networkx import DiGraph
import pyinotify

from landscaper import common
from landscaper.collector import base
from landscaper.common import LOG
from landscaper.utilities import coordinates

OSDEVTYPE_CATEGORY_MAP = {
    '0': 'storage',  # hwloc_obj_osdev_block
    '1': 'compute',  # hwloc_obj_osdev_gpu
    '2': 'network',  # hwloc_obj_osdev_network
    '3': 'network',  # hwloc_obj_osdev_openfabrics
    '4': 'compute',  # hwloc_obj_osdev_dma
    '5': 'compute',  # hwloc_obj_osdev_coproc
}

CONFIGURATION_SECTION = 'physical_layer'

# Events to listen for.
EVENTS = [pyinotify.IN_CREATE, pyinotify.IN_DELETE]



class HWLocCollector(base.Collector):
    """
    Hwloc collector. Parses all of the info for a machine from the hwloc file
    and adds it to the physical layer in the graph database.
    """
    def __init__(self, graph_db, conf_manager, events_manager):
        super(HWLocCollector, self).__init__(graph_db, conf_manager,
                                             events_manager, EVENTS)
        self.graph_db = graph_db
        self.conf_mgr = conf_manager
        self.conf_mgr.add_section(CONFIGURATION_SECTION)

    def init_graph_db(self):
        """
        Build the physical layer machines and constituent components and add to
        the graph database.
        """
        LOG.info("Adding physical machines to the landscape...")
        now_ts = time.time()
        for machine in self.conf_mgr.get_machines():
            self._add_physical_machine(machine, now_ts)
        LOG.info("Finished adding physical machines to the landscape.")

    def update_graph_db(self, event, body):
        """
        Adds new hosts to the physical layer when new hwloc file added to /data directory
        """
        LOG.info("HWLocCollector - event received: %s %s", event, body)
        folder, filename = os.path.split(body)
        # only process hwloc files added
        if filename[-10:] == "_hwloc.xml":
            device_id = filename[:-10]
            if event == pyinotify.IN_CREATE:
                LOG.info("HWLocCollector - processing: %s", filename[:-10])
                self._add_physical_machine(device_id, time.time())
            elif event == pyinotify.IN_DELETE:
                self._remove_physical_machine(device_id, time.time())

    def _add_physical_machine(self, machine, timestamp):
        """
        Add a machine to graph database using the hwloc and cpuinfo files for a
        machine.
        :param machine: Machine name.
        :param timestamp: Epoch timestamp
        """
        identity = self.graph_db.get_node_by_uuid(machine)
        if identity:
            LOG.error("Machine : %s exists in an inactive state in the landscape.", machine)
        hwloc = self._get_hwloc(machine)
        if hwloc is not None:
            LOG.info("HWLocCollector - Adding machine: %s", machine)
            graph = self._create_nxgraph_from_hwloc(hwloc, machine)
            cpu_info = self._get_cpu_info(machine)
            if cpu_info is not None:
                self._enrich_graph_cpuinfo(graph, cpu_info)
            else:
                LOG.error("No cpu info for machine: %s", machine)
            # Store the physical host in the graph database.
            self._add_coordinates(graph, machine)
            self._filter_nodes(graph)
            self.store_nxgraph_to_graph_db(graph, self.graph_db, timestamp)
        else:
            LOG.error("No hwloc details for machine: %s", machine)

    def _remove_physical_machine(self, machine, timestamp):
        identity = self.graph_db.get_node_by_uuid(machine)
        if identity:
            self.graph_db.delete_node(identity, timestamp)
            LOG.info("Machine : %s deleted from landscape", machine)
        else:
            LOG.error("Machine : %s not in the landscape to delete!", machine)
    @staticmethod
    def _add_coordinates(graph, node):
        """
        Adds coordinates to the node within the graph. As the graph is passed
        by reference the calling method gets back the graph with the
        coordinates added.
        :param graph: The graph containing the node.
        :param node: THe id of the node.
        """
        coords = coordinates.component_coordinates(node)
        graph.node[node]["attributes"]["geo"] = coords

    def _get_hwloc(self, machine):
        """
        Retrieve hwloc object for a machine.  THe object is parsed from a hwloc
        file.
        :param machine: Machine name.
        :return: Hwloc XML object.
        """
        directory = self.conf_mgr.get_hwloc_folder()
        file_name = "{}_hwloc.xml".format(machine)
        hwloc_path = os.path.abspath(os.path.join(directory, file_name))
        if self._file_exist(hwloc_path):
            return Et.parse(hwloc_path).getroot()
        return None

    def _get_cpu_info(self, machine):
        """
        Retrieve dictionary of cpuinfo for each machine cpu. The object is
        parsed from a cpuinfo file.
        :param machine: Machine name.
        :return: Dictionary of cpus and their info.
        """
        directory = self.conf_mgr.get_cpuinfo_folder()
        file_name = "{}_cpuinfo.txt".format(machine)
        cpu_info_path = os.path.abspath(os.path.join(directory, file_name))
        if self._file_exist(cpu_info_path, throw_error=False):
            return self._parse_cpu_info(cpu_info_path)
        return None

    def _parse_cpu_info(self, cpu_info_file):
        """
        Parse the text cpuinfo file and create a dict of processors.
        Each processor is a dict with all the attributes given by cpuinfo.
        :param cpu_info_file: Text file with the output of cat /proc/cpuinfo
        :return: Dictionary containing attributes of each proc
        """
        processors_dict = {}

        with open(cpu_info_file) as cpuinfo_file_handler:
            current_id = None
            for line in cpuinfo_file_handler:
                attr = line.split(':')

                if len(attr) > 1:
                    attr[0] = self.sanitize_string(attr[0])
                    attr[1] = self.sanitize_string(attr[1])

                    if 'processor' in attr[0]:
                        current_id = int(attr[1])
                        processors_dict[current_id] = {}
                        processors_dict[current_id]['id'] = attr[1]
                    elif current_id is not None and attr[1]:
                        processors_dict[current_id][attr[0]] = attr[1]

        return processors_dict

    def _create_nxgraph_from_hwloc(self, hwloc_xml, machine):
        """
        Build a graph from the hwloc file.
        :param hwloc_xml: XML object for the hwloc file.
        :param machine: Machine name.
        :return: Graph containing all of the nodes for the machine.
        """
        graph = DiGraph()
        types_count = dict()
        deleted_edges = dict()
        for child in hwloc_xml:
            if child.tag == 'object':
                self._parse_object_hwloc(types_count, graph, child, machine,
                                         deleted_edges)
        return graph

    def _parse_object_hwloc(self, types_count, graph, obj, host_name,
                            deleted_edges, parent=None):
        """
        The function parse an object and add it to the server graph.
        Then recursively it parses its children.

        :param types_count: count object per type
        :param graph: The DiGraph that represents the server
        :param obj: object extracted from hwloc xml file
        :param host_name: hostname of the machine
        :param deleted_edges: dict used to resolve the hwloc bug with cache L1
        :param parent: Parent node of the current node
        """
        object_children = []

        node_type = self.sanitize_string(obj.attrib['type'], space=False)

        if node_type == 'osdev':
            node_type = node_type + '_' + self._get_category(obj)

        node_attributes = self._get_attributes(obj, host_name)
        new_node_properties = {common.LAYER_PROP: 'physical',
                               common.CATEGORY_PROP: self._get_category(obj),
                               common.TYPE_PROP: node_type,
                               'attributes': node_attributes}

        node_name = self._get_unique_name(types_count, obj, host_name)

        attr = obj.attrib.copy()
        del attr['type']

        # Saving the children to be parsed
        for child in obj:
            if child.tag == 'object':
                object_children.append(child)

        graph.add_node(node_name, attr_dict=new_node_properties)

        # Adding the edge between current node and the parent
        if parent is not None:
            graph.add_edge(parent, node_name, label='INTERNAL')
            if parent in deleted_edges.keys():
                graph.add_edge(deleted_edges[parent], node_name,
                               label='INTERNAL')

        # Resolving the bug of hwloc that shows
        # the 2 caches L1 (data and instruction)
        # as they are one under the other
        if parent is not None:
            if new_node_properties['type'] == 'cache':
                parent_type = ''
                parent_depth = ''
                for node, node_attr in graph.nodes(data=True):
                    if node == parent:
                        parent_type = node_attr['type']
                        if parent_type == 'cache':
                            parent_depth = node_attr['attributes']['depth']

                if parent_type == new_node_properties['type'] \
                        and attr['depth'] == parent_depth:
                    graph.remove_edge(parent, node_name)
                    deleted_edges[node_name] = parent
                    parent = graph.pred[parent].keys()[0]
                    graph.add_edge(parent, node_name, label='INTERNAL')

        # Recursively calls the function to parse the child of current node
        for obj_child in object_children:
            self._parse_object_hwloc(types_count, graph, obj_child, host_name,
                                     deleted_edges, parent=node_name)

    def _filter_nodes(self, graph):
        """
        Filters out the nodes in the graph and manages hanging connections.
        As the object is pass by value, it is not returned.
        :param graph: The graph to filter.
        """
        for node_type in self.conf_mgr.get_types_to_filter():
            self.filter_nodes(graph, common.TYPE_PROP, node_type)

    def _get_unique_name(self, types_count, hw_obj, host):
        """
        Return an unique name for the hw_obj using the host name and the class
        attribute types_count that stores the number of object already parsed
        for each type.
        :param types_count: dict that stores the number of objects of same type
        :param hw_obj: object extracted from hwloc xml file
        :param host: host name
        :return a unique name.
        """

        if 'name' in hw_obj.attrib.keys():
            node_type = hw_obj.attrib['name']
        else:
            node_type = hw_obj.attrib['type']

        node_type = self.sanitize_string(node_type, space=False)

        if node_type == "machine":
            return host

        if node_type in types_count.keys():
            name = host + '_' + node_type + '_' + str(types_count[node_type])
            types_count[node_type] += 1
        else:
            name = host + '_' + node_type + '_0'
            types_count[node_type] = 1

        return name

    def _get_attributes(self, hw_obj, host_name):
        """
        Given an object from the hwloc xml file the function collects its
        attributes parsing its child having info as xml tag.
        It also adds the attributes allocation that is equal to the host_name.
        :param hw_obj: object extracted from hwloc xml file
        :param host_name: hostname of the machine,which hw_obj belongs to
        :return dictionary of attributes
        """
        attributes = hw_obj.attrib.copy()

        attributes = self.sanitize_dict(attributes)

        del attributes['type']
        attributes['allocation'] = host_name

        for child in hw_obj:
            if child.tag == 'info':
                name = self.sanitize_string(child.attrib['name'])
                value = self.sanitize_string(child.attrib['value'])
                attributes[name] = value

        return attributes

    def sanitize_dict(self, input_dict, space=True):
        """
        Sanitize keys and values of the input_dict.
        :param input_dict:
        :param space: if space is False, spaces will be replaced with _
        :return sanitized dict.
        """
        output_dict = {}
        for key in input_dict.keys():
            value = self.sanitize_string(input_dict[key], space)
            key = self.sanitize_string(key, space)
            output_dict[key] = value
        return output_dict

    @staticmethod
    def store_nxgraph_to_graph_db(graph, graph_db, timestamp=None):
        """
        Stores a networkx graph to the graph database.
        :param graph: Graph to store.
        :param graph_db: Database in which to store the graph.
        :param timestamp: Epoch timestamp.
        """
        if timestamp:
            now = timestamp
        else:
            now = time.time()

        nodes_added = dict()
        for node in graph.nodes():
            state_attr = dict()
            attributes = graph.node[str(node)]
            iden_attr = attributes.copy()
            if 'attributes' in attributes:
                state_attr = attributes['attributes']
                del iden_attr['attributes']
            nodes_added[node] = graph_db.add_node(node, iden_attr, state_attr,
                                                  now)

        for edge in graph.edges():
            source = edge[0]
            target = edge[1]
            label = 'LINKS_TO'
            if 'label' in graph.edge[source][target]:
                label = graph.edge[source][target]['label']
            src_node = nodes_added.get(source, None)
            trg_node = nodes_added.get(target, None)
            if src_node is not None and trg_node is not None:
                graph_db.add_edge(src_node, trg_node, now, label=label)

    def filter_nodes(self, graph, key, val):
        """
        Filters the nodes from the graph and manages hanging relationships.
        :param graph: Graph to filter
        :param key: key
        :param val: Value
        """
        if key is not None:
            nodes_to_filter = self.select_nodes(graph, key, val)
            for node in nodes_to_filter:
                self._filter_node(graph, node)

    @staticmethod
    def select_nodes(graph, key, val=None):
        """
        Select nodes based on key:value from the graph.
        :param graph: Graph to look in.
        :param key: key
        :param val: value
        :return: list of nodes matching the key and value.
        """
        nodes = []
        for node, attr in graph.nodes(data=True):
            if key in common.IDEN_PROPS:
                if val:
                    if key in attr and attr[key] == val:
                        nodes.append(node)
                else:
                    if key in attr:
                        nodes.append(node)
        return nodes

    def _filter_node(self, graph, node):
        """
        Filters a node from the graph and maintains connections.
        :param graph: Graph to filter
        :param node: Node to filter.
        """
        self._connect_neighbours(graph, node)
        graph.remove_node(node)

    @staticmethod
    def _connect_neighbours(graph, node):
        """
        Takes a nodes neighbours and connects them. This is done to prepare
        for the removal of the node completely.
        """
        for in_edge in graph.in_edges([node], data=True):
            label1 = 'labe1'
            if len(in_edge) > 2:
                label1 = in_edge[2].get('label', 'label1')
            for out_edge in graph.out_edges([node], data=True):
                label2 = 'label2'
                if len(out_edge) > 2:
                    label2 = out_edge[2].get('label', 'label2')
                if label1 == label2:
                    graph.add_edge(in_edge[0], out_edge[1], label=label1)
                else:
                    graph.add_edge(in_edge[0], out_edge[1])

    @staticmethod
    def _enrich_graph_cpuinfo(graph, processors_dict):
        """
        Navigate the graph and add attributes from processor_list to the PU
        nodes. The key between processor_list and hwlock_graph is the os_index
        attribute.
        :param graph: the graph that should be enriched
        :param processors_dict: a dict of cpu attributes
        """
        for node, attr in graph.nodes(data=True):
            if 'pu' in node:
                index = attr.get('attributes', dict()).get('os_index', None)
                if index is not None:
                    index = int(index)
                    processor = processors_dict.get(index, dict())
                    attr.get('attributes', dict()).update(processor)

    @staticmethod
    def _file_exist(file_name, message=None, throw_error=True):
        if not message:
            message = "File {} does not exist".format(file_name)
        if not os.path.isfile(file_name):
            if throw_error:
                raise ValueError(message + ' ' + file_name)
            else:
                return False
        return True

    @staticmethod
    def _get_category(hw_obj):
        """
        Given an object from the hwloc xml file the function return the
        category of the node choosen using the OSDETYPE_CATEGORY_MAP.
        :param hw_obj: object extracted from hwloc xml file
        :return category for this obj.
        """
        attrib = hw_obj.attrib
        if 'osdev_type' in attrib.keys():
            category = OSDEVTYPE_CATEGORY_MAP[attrib['osdev_type']]
        else:
            category = 'compute'
        return category

    @staticmethod
    def sanitize_string(input_string, space=True):
        """
        Sanitize the input_string changing it to lowercase, deleting space at
        the start and at the end.
        :param input_string:
        :param space: if space=False, spaces will be replaced with _
        :return sanitized string.
        """
        output_string = input_string.strip().lower().replace('-', '_')
        if not space:
            output_string = output_string.replace(' ', '_')
        return output_string
