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
Openstack Nova collector.
"""
import time

from landscaper.collector import base
from landscaper.common import LOG
from landscaper.utilities import openstack

# Node Structure.
IDENTITY_ATTR = {'layer': 'virtual', 'type': 'vm', 'category': 'compute'}
STATE_ATTR = {'vcpu': None, 'mem': None}

# Events to listen for.
ADD_EVENTS = ['compute.instance.create.end']

DELETE_EVENTS = ['compute.instance.delete.end',
                 'compute.instance.shutdown.end']
UPDATE_EVENTS = ['compute.instance.resize.revert.end',
                 'compute.instance.finish_resize.end',
                 'compute.instance.rebuild.end',
                 'compute.instance.update']


class NovaCollectorV2(base.Collector):
    """
    Collector for Openstack nova V2. This collector requires physical host
    collector to be ran first.
    """
    def __init__(self, graph_db, conf_manager, event_manager):
        events = ADD_EVENTS + UPDATE_EVENTS + DELETE_EVENTS
        super(NovaCollectorV2, self).__init__(graph_db, conf_manager,
                                              event_manager, events)
        self.graph_db = graph_db
        self.nova = openstack.OpenStackClientRegistry().get_nova_v2_client()

    def init_graph_db(self):
        """
        Adds the instances to the graph database and connects them to the
        relevant machine nodes.
        """
        LOG.info("Adding Nova components to the landscape.")
        now_ts = time.time()

        for instance in self.nova.servers.list():
            vcpus, mem, name, hostname = self._get_instance_info(instance)
            self._add_instance(instance.id, vcpus, mem, name, hostname, now_ts)

    def update_graph_db(self, event, body):
        """
        Updates instances.  This method is called by the events manager.
        :param event: The event that has occurred.
        :param body: The details of the event that occurred.
        """
        LOG.info("Processing event received: %s", event)
        now_ts = time.time()
        self._process_event(now_ts, event, body)

    def _process_event(self, timestamp, event, body):
        """
        Process the event based on the type of event.  The event details are
        extracted from the event body.
        :param timestamp: Epoch timestamp.
        :param event: The type of event.
        :param body: THe Event data.
        """
        uuid = body.get("payload", dict()).get("instance_id", "UNDEFINED")
        vcpus = body.get("payload", dict()).get("vcpus", "UNDEFINED")
        mem = body.get("payload", dict()).get("memory_mb", "UNDEFINED")
        name = body.get("payload", dict()).get("display_name", "UNDEFINED")
        hostname = body.get("payload", dict()).get("host", "UNDEFINED")

        if event in DELETE_EVENTS:
            self._delete_instance(uuid, timestamp)
        elif event in UPDATE_EVENTS:
            self._update_instance(uuid, vcpus, mem, name, timestamp)
        elif event in ADD_EVENTS:
            self._add_instance(uuid, vcpus, mem, name, hostname, timestamp)

    def _get_instance_info(self, instance):
        """
        Extracts instance attributes.
        :param instance: Instance object.
        :return: # vcpus, memory size. name of instance, parent machine.
        """
        flavor = self.nova.flavors.get(instance.flavor.get('id'))
        vcpus = flavor.vcpus
        mem = flavor.ram
        name = instance.name
        hostname = getattr(instance, 'OS-EXT-SRV-ATTR:hypervisor_hostname')
        return vcpus, mem, name, hostname

    def _add_instance(self, uuid, vcpus, mem, name, hostname, timestamp):
        """
        Adds a new instance to the graph database.
        :param uuid: Instance id.
        :param vcpus: Number of vcpus.
        :param mem: Size of memory.
        :param name: Instance name.
        :param hostname: Parent host.
        :param timestamp: Epoch timestamp.
        """
        identity, state = self._create_instance_nodes(vcpus, mem, name)
        inst_node = self.graph_db.add_node(uuid, identity, state, timestamp)
        machine = self._get_machine_node(hostname)

        # Creates the edge between the instance and the machine.
        if inst_node is not None and machine is not None:
            self.graph_db.add_edge(inst_node, machine,
                                   timestamp, "DEPLOYED_ON")

    def _update_instance(self, uuid, vcpus, mem, name, timestamp):
        """
        Updates an existing instance in the graph database.
        :param uuid: Instance id.
        :param vcpus: Number of vcpus.
        :param mem: Size of memory.
        :param name: Instance name.
        :param timestamp: Epoch timestamp.
        """
        identity, state = self._create_instance_nodes(vcpus, mem, name)
        self.graph_db.update_node(uuid, identity, state, timestamp)

    def _delete_instance(self, uuid, timestamp):
        """
        Deletes an instance from the graph database.
        :param uuid: UUID for the instance.
        :param timestamp: epoch timestamp.
        """
        instance_node = self.graph_db.get_node_by_uuid(uuid)
        if instance_node:
            self.graph_db.delete_node(instance_node, timestamp)

    def _get_machine_node(self, hostname):
        """
        Returns an instance of a machine graph database node.
        :param hostname: Name of the hostname to retrieve.
        :return: Instance of a machine node for a graph database.
        """
        machine = self.graph_db.get_node_by_uuid(hostname)
        return machine

    @staticmethod
    def _create_instance_nodes(vcpus, mem, name):
        """
        Creates the identity and state node for an instance.  They are created
        using the standard attributes for each instance, identity and state
        node.
        :param vcpus: Number of vcpus on the instance.
        :param mem: Size of memory on the instance.
        :param name: Name of the instance.
        :return: State and instnace nodes.
        """
        identity_node = IDENTITY_ATTR.copy()
        state_node = STATE_ATTR.copy()
        state_node["vcpu"] = vcpus
        state_node["mem"] = mem
        state_node["vm_name"] = name
        return identity_node, state_node
