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
Adds physical switches to the landscape.
"""
import time
import yaml

from landscaper import paths
from landscaper.collector import base
from landscaper.common import LOG

# Structure of the switch nodes.
IDENTITY = {'type': 'switch', 'layer': 'physical', 'category': 'network'}
STATE = {'switch_name': None, 'bandwidth': None, 'roles': None, 'address': None}


class PhysicalNetworkCollector(base.Collector):
    """
    Adds the physical network to the landscape. Adds switches and connects
    them to connected devices.
    """
    def __init__(self, graph_db, conf_manager, events_manager):
        super(PhysicalNetworkCollector, self).__init__(graph_db, conf_manager,
                                                       events_manager)
        self.graph_db = graph_db

    def init_graph_db(self):
        LOG.info("[PHYS NETWORK] Adding physical network.")
        net_description = self._network_description(paths.NETWORK_DESCRIPTION)
        # Use two loops for inter switch connections.
        for switch, switch_info in net_description.iteritems():
            self._add_switch(switch, switch_info, time.time())
        for switch, switch_info in net_description.iteritems():
            self._connect_switches(switch, switch_info, time.time())

    def update_graph_db(self, event, body):
        pass

    def _add_switch(self, switch_id, switch_info, timestamp):
        # Add the switch node.
        iden, state = self._create_switch_nodes(switch_info)
        switch = self.graph_db.add_node(switch_id, iden, state, timestamp)
        self.graph_db.add_node(switch_id, iden, state, timestamp)

    def _connect_switches(self, switch_id, switch_info, timestamp):
        switch = self.graph_db.get_node_by_uuid(switch_id)
        for dev_id in switch_info.get('connected-devices', []):
            device = self._the_node(dev_id)
            if device:
                self.graph_db.add_edge(device, switch, timestamp, "COMMUNICATES")
            else:
                LOG.warning("Couldn't connect device '%s' to switch '%s'", dev_id,
                            switch_id)

    def _the_node(self, device_id):
        nic_node = None
        device_id = device_id.lower()
        nodes = self.graph_db.get_nodes_by_properties({"address": device_id})
        if nodes:
            predecessors = self.graph_db.predecessors(nodes[0])
            if predecessors:
                nic_node = predecessors[0][0]
        return nic_node

    @staticmethod
    def _network_description(network_desc_file):
        return yaml.load(open(network_desc_file))

    @staticmethod
    def _create_switch_nodes(switch_info):
        identity_node = IDENTITY.copy()
        state_node = STATE.copy()
        state_node['switch_name'] = switch_info.get('name')
        state_node['bandwidth'] = switch_info.get('bandwidth')
        state_node['roles'] = switch_info.get('roles', [])
        state_node['address'] = switch_info.get('address')
        return identity_node, state_node