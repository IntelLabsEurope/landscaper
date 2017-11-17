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
Openstack neutron collector.
"""
import time

from landscaper.collector import base
from landscaper.common import LOG
from landscaper.utilities import openstack

# Node Structure.
SUBNET_IDEN_ATR = {'layer': 'virtual', 'type': 'subnet', 'category': 'network'}
NET_IDEN_ATTR = {'layer': 'virtual', 'type': 'network', 'category': 'network'}
PORT_IDEN_ATTR = {'layer': 'virtual', 'type': 'vnic', 'category': 'network'}
PORT_STATE_ATTR = {'mac': None, 'ip': None}
SUBNET_STATE_ATTR = {'cidr': None}
NET_STATE_ATTR = {'name': None}

# Events to listen for.
NET_ADD_EVENTS = ['network.create.end']
NET_UPDATE_EVENTS = ['network.update.end']
NET_DELETE_EVENTS = ['network.delete.end']
SUBNET_ADD_EVENTS = ['subnet.create.end']
SUBNET_UPDATE_EVENTS = ['subnet.update.end']
SUBNET_DELETE_EVENTS = ['subnet.delete.end']
PORT_ADD_EVENTS = ['port.create.end']
PORT_UPDATE_EVENTS = ['port.update.end', 'router.interface.create']
PORT_DELETE_EVENTS = ['port.delete.end', 'router.interface.delete']


class NeutronCollectorV2(base.Collector):
    """
    Adds neutron ports, networks and subnets to the landscape.
    """
    def __init__(self, graph_db, conf_manager, event_manager):
        events = self._events()
        super(NeutronCollectorV2, self).__init__(graph_db, conf_manager,
                                                 event_manager, events)
        self.graph_db = graph_db
        ocr = openstack.OpenStackClientRegistry()
        self.neutron = ocr.get_neutron_v2_client()

    def init_graph_db(self):
        """
        Adds all neutron ports, nets and subnets to the graph database.
        """
        LOG.info("Adding Neutron components to the landscape.")
        now_ts = time.time()
        # Collect Networks
        networks = self.neutron.list_networks()
        for net in networks.get('networks', list()):
            net_id = net.get('id', "UNDEFINED")
            net_name = net.get('name', "UNDEFINED")
            self._add_network(net_id, net_name, now_ts)

        # Collect subnets
        subnets = self.neutron.list_subnets()
        for subnet in subnets.get('subnets', list()):
            subnet_id = subnet.get('id', "UNDEFINED")
            cidr = subnet.get('cidr', "UNDEFINED")
            network_id = subnet.get('network_id', "UNDEFINED")
            self._add_subnet(subnet_id, cidr, network_id, now_ts)

        # Collect ports
        ports = self.neutron.list_ports()
        for port in ports.get('ports', list()):
            port_id = port.get("id", "UNDEFINED")
            mac, fixed_ip, device_id, net_id = self._get_port_info(port)
            self._add_port(port_id, mac, fixed_ip, device_id, net_id, now_ts)

    def update_graph_db(self, event, body):
        """
        Receives events from neutron and updates the graph database.
        :param event: Neutron event type.
        :param body: Event details.
        """
        LOG.info("Neutron event received: %s", event)
        now_ts = time.time()
        net_events, port_events, subnet_events = self._events(categories=True)

        if event in port_events:
            self._manage_port(event, body, now_ts)
        elif event in net_events:
            self._manage_net(event, body, now_ts)
        elif event in subnet_events:
            self._manage_subnet(event, body, now_ts)

    def _manage_port(self, event, body, timestmp):
        """
        Manage port event actions.
        :param event: Neutron event type.
        :param body: Neutron event details.
        :param timestmp: timestamp.
        """
        if event in PORT_DELETE_EVENTS:
            port = body.get("payload", dict()).get("port_id", "UNDEFINED")
            self._delete_port(port, timestmp)
        else:
            # Get port details
            port_attr = body.get("payload", dict()).get("port", dict())
            port = port_attr.get("id", "UNDEFINED")
            mac = port_attr.get("mac_address", "UNDEFINED")
            fixd_ip = "UNDEFINED"
            for ips in port_attr.get("fixed_ips", list()):
                fixd_ip = ips.get('ip_address', "UNDEFINED")
            net_id = port_attr.get("network_id", "UNDEFINED")
            dev_id = port_attr.get("device_id", "UNDEFINED")

            # Add/Update Event.
            if event in PORT_ADD_EVENTS:
                self._add_port(port, mac, fixd_ip, dev_id, net_id, timestmp)
            elif event in PORT_UPDATE_EVENTS:
                self._update_port(port, mac, fixd_ip, dev_id, net_id, timestmp)

    def _manage_subnet(self, event, body, timestamp):
        """
        Manage subnet event actions.
        :param event: Neutron event type.
        :param body: Neutron event details.
        :param timestamp: timestamp.
        """
        if event in SUBNET_DELETE_EVENTS:
            subnet_id = body.get("payload", {}).get("subnet_id", "UNDEFINED")
            self._delete_subnet(subnet_id, timestamp)
        else:
            # Get subnet details.
            subnet_attr = body.get("payload", dict()).get("subnet", dict())
            subnet_id = subnet_attr.get("id", "UNDEFINED")
            cidr = subnet_attr.get("cidr", "UNDEFINED")
            net_id = subnet_attr.get("network_id", "UNDEFINED")

            # Add/Update subnet.
            if event in SUBNET_ADD_EVENTS:
                self._add_subnet(subnet_id, cidr, net_id, timestamp)
            elif event in SUBNET_UPDATE_EVENTS:
                self._update_subnet(subnet_id, cidr, net_id, timestamp)

    def _manage_net(self, event, body, timestamp):
        """
        Manage net event actions.
        :param event: Neutron event type.
        :param body: Neutron event details.
        :param timestamp: timestamp.
        """
        if event in NET_DELETE_EVENTS:
            net_id = body.get("payload", dict()).get("network_id", "UNDEFINED")
            self._delete_network(net_id, timestamp)
        else:
            # Get network details.
            net_attr = body.get("payload", dict()).get("network", dict())
            network_id = net_attr.get("id", "UNDEFINED")
            network_name = net_attr.get("name", "UNDEFINED")

            # Add/Update network.
            if event in NET_ADD_EVENTS:
                self._add_network(network_id, network_name, timestamp)
            elif event in NET_UPDATE_EVENTS:
                self._update_network(network_id, network_name, timestamp)

    def _add_subnet(self, subnet_id, cidr, net_id, timestmp):
        """
        Add subnet node to the database.
        """
        identy, state = self._create_subnet_nodes(cidr)
        net_node = self._get_net_node(net_id)

        # if the net node exist means the network is active.
        if net_node is not None:
            subnet_node = self.graph_db.add_node(subnet_id, identy, state,
                                                 timestmp)
            self.graph_db.add_edge(subnet_node, net_node, timestmp, "REQUIRES")

    def _update_subnet(self, subnet_id, cidr, net_id, timestamp):
        """
        Update existing subnet node in the database.
        """
        identity, state = self._create_subnet_nodes(cidr)
        net_node = self._get_net_node(net_id)

        if net_node is not None:
            subnet_node = self.graph_db.update_node(subnet_id, identity,
                                                    state, timestamp)
            self.graph_db.update_edge(subnet_node, net_node,
                                      timestamp, "REQUIRES")

    def _delete_subnet(self, subnet_id, timestamp):
        """
        Delete existing subnet node from the database.
        """
        subnet_node = self.graph_db.get_node_by_uuid(subnet_id)
        if subnet_node:
            self.graph_db.delete_node(subnet_node, timestamp)

    def _add_network(self, network_id, name, timestamp):
        """
        Add network node to the database.
        """
        identity, state = self._create_network_nodes(name)
        self.graph_db.add_node(network_id, identity, state, timestamp)

    def _update_network(self, network_id, name, timestamp):
        """
        Update existing network node in the database.
        """
        identity, state = self._create_network_nodes(name)
        self.graph_db.update_node(network_id, identity, state, timestamp)

    def _delete_network(self, network_id, timestamp):
        """
        Delete existing network node from the database.
        """
        net_node = self.graph_db.get_node_by_uuid(network_id)
        if net_node:
            self.graph_db.delete_node(net_node, timestamp)

    def _add_port(self, port_id, mac, ip_addr, device_id, net_id, timestamp):
        """
        Add port node to the database.
        """
        identity, state = self._create_port_nodes(mac, ip_addr)
        instance = self._get_device_node(device_id)
        port = self.graph_db.add_node(port_id, identity, state, timestamp)

        if port is not None:
            if instance is not None:
                self.graph_db.add_edge(instance, port, timestamp, "REQUIRES")
            net_node = self._get_net_node(net_id)
            if net_node is not None:
                self.graph_db.add_edge(port, net_node, timestamp, "REQUIRES")

    def _update_port(self, port_id, mac, ip_add, device_id, net_id, timestmp):
        """
        Update existing port node in the database.
        """
        identity, state = self._create_port_nodes(mac, ip_add)
        instance = self._get_device_node(device_id)
        port = self.graph_db.update_node(port_id, identity, state, timestmp)

        if port is not None:
            if instance is not None:
                self.graph_db.update_edge(instance, port, timestmp, "REQUIRES")
            net_node = self._get_net_node(net_id)
            if net_node is not None:
                self.graph_db.update_edge(port, net_node, timestmp, "REQUIRES")

    def _delete_port(self, port_id, timestamp):
        """
        Delete existing port node from the database.
        """
        port_node = self.graph_db.get_node_by_uuid(port_id)
        if port_node:
            self.graph_db.delete_node(port_node, timestamp)

    @staticmethod
    def _get_port_info(port):
        """
        Returns port info.
        :param port: port object.
        :return: Port info.
        """
        mac = port.get("mac_address", "UNDEFINED")
        fixed_ip = "UNDEFINED"
        device_id = port.get("device_id", "UNDEFINED")
        net_id = port.get("network_id", "UNDEFINED")
        for ips in port.get("fixed_ips", list()):
            fixed_ip = ips.get('ip_address', "UNDEFINED")

        return mac, fixed_ip, device_id, net_id

    @staticmethod
    def _create_subnet_nodes(cidr):
        """
        Creates state and identity nodes for the subnet.
        :param cidr: cidr.
        :return: State and identity nodes for the subnet.
        """
        identity = SUBNET_IDEN_ATR.copy()
        state = SUBNET_STATE_ATTR.copy()
        state["cidr"] = cidr
        return identity, state

    @staticmethod
    def _create_network_nodes(network_name):
        """
        Creates state and identity nodes for the network.
        :param network_name: Name of the network.
        :return: State and identity nodes for the network.
        """
        identity = NET_IDEN_ATTR.copy()
        state = NET_STATE_ATTR.copy()
        state["name"] = network_name
        return identity, state

    @staticmethod
    def _create_port_nodes(mac_address, ip_address):
        """
        Creates state and identity nodes for the network.
        :param mac_address: mac address.
        :param ip_address: ip address.
        :return: State and identity nodes for the port.
        """
        identity = PORT_IDEN_ATTR.copy()
        state = PORT_STATE_ATTR.copy()
        state['mac'] = mac_address
        state['ip'] = ip_address
        return identity, state

    def _get_device_node(self, device_id):
        """
        Returns device node from the database.
        """
        return self.graph_db.get_node_by_uuid(device_id)

    def _get_net_node(self, net_id):
        """
        Returns network node from the database.
        """
        return self.graph_db.get_node_by_uuid(net_id)

    @staticmethod
    def _events(categories=False):
        """
        Returns all events.
        """
        net_events = NET_ADD_EVENTS + NET_UPDATE_EVENTS + NET_DELETE_EVENTS
        port_events = PORT_ADD_EVENTS + PORT_UPDATE_EVENTS + PORT_DELETE_EVENTS
        subnet_events = (SUBNET_ADD_EVENTS + SUBNET_UPDATE_EVENTS +
                         SUBNET_DELETE_EVENTS)
        if categories:
            return net_events, port_events, subnet_events
        return net_events + port_events + subnet_events
