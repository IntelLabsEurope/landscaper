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
Ephemeral disk collector.
"""
import threading
import time
import xml.etree.ElementTree as ET
import socket
import paramiko
from paramiko import ssh_exception

from landscaper.collector import base
from landscaper.common import LOG


DISK_IDEN_ATTR = {'layer': 'virtual', 'type': 'disk', 'category': 'storage'}

# Events to listen for.
DELETE_EVENTS = ['compute.instance.delete.end',
                 'compute.instance.shutdown.end']
CREATED_EVENTS = ['compute.instance.create.end']
SSH_TIMEOUT = 10
CONFIGURATION_SECTION = 'physical_layer'


class EphemeralDiskCollector(base.Collector):
    """
    Collector for Ephemeral Disk. This collector requires Nova
    collector to be ran first.
    """
    def __init__(self, graph_db, conf_manager, event_manager):
        events = CREATED_EVENTS + DELETE_EVENTS
        super(EphemeralDiskCollector, self).__init__(graph_db, conf_manager,
                                                     event_manager, events)
        self.graph_db = graph_db
        self.conf_mgr = conf_manager
        self.hosts = []
        for machine in self.conf_mgr.get_machines():
            self.hosts.append(machine)
        self.instance_disks = {}
        self.instance_disk_lookup = {}

    def init_graph_db(self):
        """
        Adds the instances to the graph database and connects them to the
        relevant machine nodes.
        """
        LOG.info("[EDISK] Adding ephemeral_disk components to the landscape.")
        now_ts = time.time()
        self._retrieve_instance_disks()
        for instance_id, disk_obj in self.instance_disks.iteritems():
            self.attach_disk_to_instance(instance_id, disk_obj, now_ts)

    def attach_disk_to_instance(self, uuid, disk_obj, timestamp):
        """
        Attaches ephemeral disks to the instance.
        :param uuid:
        :param disk_obj:
        :param timestamp:
        :return:
        """
        inst_node = self.graph_db.get_node_by_uuid(uuid)
        self._attach_instance_disks(inst_node, disk_obj, timestamp)

    def update_graph_db(self, event, body):
        """
        Updates instances.  This method is called by the events manager.
        :param event: The event that has occurred.
        :param body: The details of the event that occurred.
        """
        LOG.info("[EPHEMERAL DISK] Processing event received: %s", event)
        current_ts = time.time()
        self._process_event(current_ts, event, body)

    def _process_event(self, timestamp, event, body):
        """
        Process the event based on the type of event.  The event details are
        extracted from the event body.
        :param timestamp: Epoch timestamp.
        :param event: The type of event.
        :param body: THe Event data.
        """
        default = "UNDEFINED"
        uuid = body.get("payload", dict()).get("instance_id", default)
        hostname = body.get("payload", dict()).get("host", default)

        # Add the ephemeral disks after the vm has been created.
        if event in CREATED_EVENTS:
            self._host_ephemeral_disks(hostname)
            disk_obj = self.instance_disks[uuid]
            self.attach_disk_to_instance(uuid, disk_obj, timestamp)
        elif event in DELETE_EVENTS:
            self._delete_instance(uuid, timestamp)

    def _delete_instance(self, uuid, timestamp):
        """
        Deletes an instance from the graph database.
        :param uuid: UUID for the instance.
        :param timestamp: epoch timestamp.
        """
        # Delete ephemeral disks attached to the instance
        instance_disks = self.instance_disk_lookup.get(uuid, [])
        for disk_uuid in instance_disks:
            disk_node = self.graph_db.get_node_by_uuid(disk_uuid)
            if disk_node:
                self.graph_db.delete_node(disk_node, timestamp)

    def _get_machine_node(self, hostname):
        """
        Returns an instance of a machine graph database node.
        :param hostname: Name of the hostname to retrieve.
        :return: Instance of a machine node for a graph database.
        """
        machine = self.graph_db.get_node_by_uuid(hostname)
        return machine

    def _retrieve_instance_disks(self):
        """
        Queries the hosts for their ephemeral disks and stores them in class
        instance variable.
        """
        self._load_ephemeral_disks(self.hosts)

    def _attach_instance_disks(self, instance_node, disks, timestamp):
        disk_ids = []
        for disk_id, disk_attr in disks:
            identity, state = self._create_disk_nodes(disk_attr)
            uuid = "{}_{}".format(instance_node["name"], disk_id)

            node = self.graph_db.add_node(uuid, identity, state, timestamp)
            self.graph_db.add_edge(instance_node, node, timestamp, "ON")
            disk_ids.append(uuid)
        self.instance_disk_lookup[instance_node["name"]] = disk_ids

    @staticmethod
    def _create_disk_nodes(disk_attr):
        identity_node = DISK_IDEN_ATTR.copy()
        state_node = disk_attr
        return identity_node, state_node

    @staticmethod
    def _ssh_client(host):
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.load_system_host_keys()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(host, timeout=SSH_TIMEOUT)
        except (ssh_exception.NoValidConnectionsError, socket.error,
                ssh_exception.AuthenticationException) as err:
            LOG.error("Could not add ephemeral disks for host: %s", host)
            LOG.error("SSH Error for host %s: %s", host, err)
            return None
        return ssh_client

    @staticmethod
    def _disk_info(disk):
        dev_id = disk.find("target").get("dev")
        driver = disk.find("driver").attrib
        attributes = {"driver_" + key: val for key, val in driver.items()}
        if disk.get("type") == "network":
            attributes["physical_disk"] = disk.find("auth/secret").get("type")
        else:
            attributes["physical_disk"] = disk.get("type")
        attributes["disk_name"] = dev_id
        return dev_id, attributes

    def _instance_disks(self, libvirtdump):
        root = ET.fromstring(libvirtdump)
        instance_id = root.find("uuid").text
        dev_ids = []
        for disk in root.findall("devices/disk"):
            if disk.get("device") == "disk":
                if disk.get("type") == "network" or disk.get("type") == "file":
                    dev_ids.append(self._disk_info(disk))

        return instance_id, dev_ids

    def _load_ephemeral_disks(self, hosts):
        threads = []
        for host in hosts:
            host_thread = threading.Thread(target=self._host_ephemeral_disks,
                                           args=(host,))
            threads.append(host_thread)
            host_thread.start()

        for thr in threads:
            thr.join()

    def _host_ephemeral_disks(self, host):
        ssh_client = self._ssh_client(host)
        if ssh_client:
            libvirt_instances = self._libvirt_domains(ssh_client)
            for libvirt_inst in libvirt_instances:
                cmd = "virsh dumpxml {}".format(libvirt_inst)
                _, stdout, _ = ssh_client.exec_command(cmd)
                xml_dump = stdout.read().strip()
                instance_id, instance_disks = self._instance_disks(xml_dump)
                self.instance_disks[instance_id] = instance_disks

    @staticmethod
    def _libvirt_domains(ssh_client):
        _, stdout, _ = ssh_client.exec_command("virsh list")
        lines = stdout.read().split('\n')[2:]
        domains = []
        for line in lines:
            if line:
                domains.append(line.strip().split()[1])
        return domains
