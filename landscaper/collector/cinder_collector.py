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
Openstack Cinder collector class.
"""
import time

from landscaper.collector import base
from landscaper.common import LOG
from landscaper.utilities import openstack

# Node Structure.
IDEN_ATTR = {'layer': 'virtual', 'type': 'volume', 'category': 'storage'}
STATE_ATTR = {'size': None}

# Events to listen for.
ADD_EVENTS = ['volume.create.end']
DELETE_EVENTS = ['volume.delete.end']
UPDATE_EVENTS = ['volume.update.end',
                 'volume.resize.end',
                 'volume.attach.end',
                 'volume.detach.end']


class CinderCollectorV2(base.Collector):
    """
    Collects volume information from cinder and adds to the landscape as a
    volume node.
    """
    def __init__(self, graph_db, conf_manager, event_manager):
        events = ADD_EVENTS + UPDATE_EVENTS + DELETE_EVENTS
        super(CinderCollectorV2, self).__init__(graph_db, conf_manager,
                                                event_manager, events)
        self.graph_db = graph_db
        ocr = openstack.OpenStackClientRegistry()
        self.cinder = ocr.get_cinder_v2_client()

    def init_graph_db(self):
        """
        Add Volume nodes to the landscape.
        """
        LOG.info("[CINDER] Adding Cinder components to the landscape.")
        now_ts = time.time()
        for volume in self.cinder.volumes.list():
            volume_id, size, hostname, vm_id = self._get_volume_info(volume)
            self._add_volume(volume_id, size, hostname, vm_id, now_ts)

    def update_graph_db(self, event, body):
        """
        Updates, adds and deletes cinder volumes based on the event type.
        :param event: Event type.
        :param body: Event details.
        """
        LOG.info("[CINDER] Cinder event received: %s.", event)
        now_ts = time.time()
        uuid = body.get("payload", dict()).get("volume_id", "UNDEFINED")
        size = body.get("payload", dict()).get("size", "UNDEFINED")
        hostname = body.get("payload", dict()).get("host", "UNDEFINED")
        if hostname:
            if "#" in hostname:
                hostname = hostname.split("#")[0]
            if "@" in hostname:
                hostname = hostname.split('@')[0]

        attachments = body.get("payload", dict()).get('volume_attachment', [])

        vm_id = "UNDEFINED"
        for attachment in attachments:
            attach_status = attachment.get("attach_status", "UNDEFINED")
            if attach_status == "attached":
                vm_id = attachment.get('instance_uuid', "UNDEFINED")

        if event in DELETE_EVENTS:
            self._delete_volume(uuid, now_ts)
        elif event in UPDATE_EVENTS:
            self._update_volume(uuid, size, hostname, vm_id, now_ts)
        elif event in ADD_EVENTS:
            self._add_volume(uuid, size, hostname, vm_id, now_ts)

    def _add_volume(self, uuid, size, hostname, instance_id, timestamp):
        """
        Adds the volume to the landscape and connects it to the attached
        instance.
        """
        identity, state = self._create_volume_nodes(size)

        volume_node = self.graph_db.add_node(uuid, identity, state, timestamp)
        if volume_node is not None:
            machine = self._get_machine_node(hostname)
            if machine is not None:
                self.graph_db.add_edge(volume_node, machine,
                                       timestamp, "DEPLOYED_ON")

            instance_node = self._get_device_node(instance_id)
            if instance_node is not None:
                self.graph_db.add_edge(instance_node, volume_node,
                                       timestamp, "REQUIRES")

    def _update_volume(self, uuid, size, hostname, instance_id, timestamp):
        """
        Updates the volume by changing the state node.
        """
        _, state = self._create_volume_nodes(size)
        volume_node, _ = self.graph_db.update_node(uuid, timestamp, state)
        if volume_node is not None:
            machine = self._get_machine_node(hostname)
            if machine is not None:
                self.graph_db.update_edge(volume_node, machine,
                                          timestamp, "DEPLOYED_ON")

            vm_node = self._get_device_node(instance_id)
            if vm_node is not None:
                self.graph_db.update_edge(vm_node, volume_node,
                                          timestamp, "REQUIRES")

    def _delete_volume(self, volume_id, timestamp):
        """
        Deletes the volume from the landscape.
        """
        volume_node = self.graph_db.get_node_by_uuid(volume_id)
        if volume_node is not None:
            self.graph_db.delete_node(volume_node, timestamp)

    @staticmethod
    def _create_volume_nodes(size):
        """
        Creates the identity and state node for a volume.
        """
        iden = IDEN_ATTR.copy()
        state = STATE_ATTR.copy()
        state['size'] = size
        return iden, state

    def _get_machine_node(self, hostname):
        """
        Returns an instance of a machine node from the landscape.
        :param hostname: Name of the hostname to retrieve.
        :return: Instance of a machine node.
        """
        machine = self.graph_db.get_node_by_uuid(hostname)
        return machine

    @staticmethod
    def _get_volume_info(volume):
        """
        Returns volume information.
        :param volume: Cinder Volume Object.
        :return: volume_id, volume size, host, attached instance
        """
        info = volume._info
        volume_id = info.get("id")
        size = info.get("size", "UNDEFINED")
        host = info.get("os-vol-host-attr:host", "UNDEFINED")
        if host is not None:
            if "#" in host:
                host = host.split("#")[0]
            if "@" in host:
                host = host.split('@')[0]
        else:
            host = "UNDEFINED"

        vm_id = "UNDEFINED"
        attachments = info.get("attachments", list())
        if attachments:
            attachment = attachments[0]
            vm_id = attachment.get("server_id", "UNDEFINED")

        return volume_id, size, host, vm_id

    def _get_device_node(self, device_id):
        """
        Return an instance of the volume device from the landscape.
        """
        return self.graph_db.get_node_by_uuid(device_id)
