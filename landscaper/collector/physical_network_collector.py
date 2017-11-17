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
STATE = {'switch_name': None, 'bandwidth': None, 'roles': None}


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
        LOG.info("Adding physical network.")
        net_description = self._network_description(paths.NETWORK_DESCRIPTION)
        for switch, switch_info in net_description.iteritems():
            self._add_switch(switch, switch_info, time.time())

    def update_graph_db(self, event, body):
        pass

    def _add_switch(self, switch_id, switch_info, timestamp):
        # Add the switch node.
        iden, state = self._create_switch_nodes(switch_info)
        switch = self.graph_db.add_node(switch_id, iden, state, timestamp)

        # Connect the switch node to the nics
        for mac in switch_info.get('connected-devices', []):
            nic = self._nic_node(mac)
            if nic:
                self.graph_db.add_edge(nic, switch, timestamp, "COMMUNICATES")
            else:
                LOG.warning("Couldn't connect device '%s' to switch '%s'", mac,
                            switch_id)

    def _nic_node(self, mac_address):
        nic_node = None
        mac_address = mac_address.lower()
        nodes = self.graph_db.get_nodes_by_properties({"address": mac_address})
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
        return identity_node, state_node
