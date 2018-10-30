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
Load Use Case Collector
"""
from xml.etree import ElementTree as et
import random
import os
import shutil
import yaml
import pyexcel

from landscaper.collector import base
from landscaper.common import LOG
from landscaper import paths

_MAX_GENERATION = 1000


class UseCaseCollector(base.Collector):
    """
    UseCase collector. Imports excel file with a use case landscape separated
    into two sheets; Nodes and Links. Converts the excel sheets to .csv format.
    Creates hwloc and cpuinfo files for the servers connected to every network
    switch saves files in the Data Directory.
    """
    def __init__(self, graph_db, conf_manager, events_manager, events=None):
        super(UseCaseCollector, self).__init__(graph_db, conf_manager,
                                               events_manager, events=None)
        self.cnf = conf_manager
        self.mac_addresses = []

    def init_graph_db(self):
        """
        Import excel file, create two .csv files for the nodes and edges in
        the landscape. Create two servers for each network switch in the
        landscape. Generate hwloc and cpuinfo for each machine and add files
        to the Data Directory. Create a network_description.yaml file with
        connections to servers and network switches.
        """
        LOG.info("Deleting hwloc and cpuifo files")
        # Deleting hwloc and cpuinfo files is necessary for testing collector
        filelist = [file for file in os.listdir(paths.DATA_DIR) if
                    file.endswith(".txt") or file.endswith('.xml') or
                    file.endswith('.yaml')]
        for file in filelist:
            os.remove(os.path.join(paths.DATA_DIR, file))

        if os.path.exists(os.path.join(paths.DATA_DIR, "nodes.csv")) and \
                os.path.exists(os.path.join(paths.DATA_DIR, "links.csv")):

            node_array = pyexcel.get_sheet(file_name=os.path.join(
                paths.DATA_DIR, "nodes.csv"), name_columns_by_row=0)
            attributes = list(node_array.colnames)
            link_array = pyexcel.get_sheet(file_name=os.path.join(
                paths.DATA_DIR, "links.csv"), name_columns_by_row=0)

            LOG.info("Creating hwloc, cpu_info and network description files")
            for node in node_array:
                if node[1] == 'network' and node[2] == 'switch':
                    connections = []
                    node_id = node[0]
                    links = self._search_links(link_array, node[0])
                    for element in range(1, node[3] + 1):
                        mac_address = self._create_hwloc_file(node_id, element)
                        self._create_cpuinfo_file(node_id, element)
                        connections.append(mac_address)
                    connections.extend(links)
                    self._add_network_switch(node, attributes, connections)
                else:
                    LOG.error("Node.csv file does not contain network switch data")

        else:
            LOG.error("CSV Files not in data directory")

    def update_graph_db(self, event, body):
        """
        Not implemented as there is no update events for DataClay or this one either.
        """
        raise NotImplementedError

    def _generate_mac_address(self):
        """
        Generate a unique fake mac address for each server.
        Change hwloc template if server information provided by Use Case provider.
        :return random_mac: unique MAC address
        """
        for _ in range(_MAX_GENERATION):
            random_mac = "%02x:%02x:%02x:%02x:%02x:%02x" % (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )

            if random_mac not in self.mac_addresses:
                self.mac_addresses.append(random_mac)
                return random_mac.upper()

    def _build_hwloc_object(self, node_id, index):
        """
        Build hwloc object
        :param node_id: unique id for each network switch
        :param index: number given to the server for the given network switch
        :return mac_address: mac_address for server
        :return tree: hwloc object
        """
        tree = et.parse(paths.TEMP_HWLOC)
        root = tree.getroot()

        for info in root.findall("object/info"):
            name = info.get('name')
            if name.lower() == 'hostname':
                info.set('value', "{}-{}".format(node_id, index))

        for element in tree.iter('info'):
            value = element.get('value')
            if value == 'ENTER_MAC':
                mac_address = self._generate_mac_address()
                element.set('value', mac_address)
        return mac_address, tree

    def _create_hwloc_file(self, node_id, index):
        """
        Write hwloc object to .xml file in data directory
        :param node_id: unique id for each network switch
        :param index: number given to the server for the given network switch
        """
        mac_address, hwloc = self._build_hwloc_object(node_id, index)
        hwloc.write(os.path.join(paths.DATA_DIR, "{}-{}_hwloc.xml"
                                 .format(node_id, index)))
        return mac_address

    @staticmethod
    def _create_cpuinfo_file(node_id, index):
        """
        Create cpuinfo file using the template for each physical machine
        :param node_id: unique id for each network switch
        :param index: number given to the server for the given network switch
        """
        source = paths.TEMP_CPUINFO
        destination = paths.DATA_DIR
        shutil.copy(source, destination)
        os.rename(os.path.join(destination, 'template_cpuinfo.txt'),
                  os.path.join(destination, '{}-{}_cpuinfo.txt'
                               .format(node_id, index)))

    @staticmethod
    def _search_links(link_array, node_id):
        """
        Search links.csv for connections between network switches
        :param link_array: list of connections between network switches
        :param node_id: unique id for each network switch
        :return: links: network switches connected to node_id
        """
        links = []
        for link in link_array:
            if node_id == link[1]:
                links.append(link[0])
        return links

    @staticmethod
    def _add_network_switch(node, attributes, connections):
        """
        Add network switch data to the network description file
        :param node: network switch unique id and values for attributes
        :param attributes: key attribute names
        :param connections: list of network switch's connected devices
        """
        i = 0
        switch_attributes = attributes[4:]
        node_attributes = node[4:]
        switch_data = {node[0]: {attributes[0]: node[0]}}
        for item in switch_attributes:
            switch_data[node[0]][item] = node_attributes[i]
            i = i+1

        switch_data[node[0]]['address'] = node[0].lower()
        switch_data[node[0]]['connected-devices'] = connections
        with open(os.path.join(paths.DATA_DIR, "network_description.yaml"), 'a') as yaml_file:
            yaml.safe_dump(switch_data, yaml_file, default_flow_style=False)
