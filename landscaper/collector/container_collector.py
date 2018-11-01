# Copyright 2017 Intel Corporation
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
import threading
import time

from landscaper.collector import base
from landscaper.common import LOG
from landscaper.utilities import configuration
from landscaper import events_manager
import docker

# Node Structure.
IDENTITY_ATTR = {'layer': 'virtual', 'type': 'docker_node', 'category': 'compute'}
STATE_ATTR = {'node_name': None}

# Events to listen for.
ADD_EVENTS = ['dockerhost.create']
DELETE_EVENTS = ['dockerhost.remove']
UPDATE_EVENTS = ['dockerhost.update']

CONFIG_SECTION = 'docker'

# TODO: handle multiple separate swarms

class ContainerCollectorV1(base.Collector):
    """
    Collector for Docker Node infrastructure. This collector requires physical
    host collector to be run first. Will add swarm nodes for master and slaves
    """
    def __init__(self, graph_db, conf_manager, event_manager):
        events = ADD_EVENTS + UPDATE_EVENTS + DELETE_EVENTS
        super(ContainerCollectorV1, self).__init__(graph_db, conf_manager,
                                              event_manager, events)
        self.graph_db = graph_db
        conf_manager.add_section(CONFIG_SECTION)
        docker_conf = conf_manager.get_swarm_info()
        self.swarm_manager = ContainerCollectorV1.get_swarm_manager(docker_conf)
        self.instance_disks = {}
        self.instance_disk_lookup = {}

    def init_graph_db(self):
        """
        Adds the instances to the graph database and connects them to the
        relevant machine nodes.
        """
        LOG.info("ContainerCollector - Adding Docker infrastructure components to the landscape.")
        now_ts = time.time()
        nodes = [x for x in self.swarm_manager.nodes.list() if
                 x.attrs["Status"]["State"] == 'ready']
        for node in nodes:
            node_id = node.attrs["ID"]
            hostname = node.attrs['Description']['Hostname']
            if 'ManagerStatus' in node.attrs:
                addr = node.attrs['ManagerStatus']['Addr']
            else:
                addr = node.attrs['Status']['Addr']
            state_attributes = self._get_instance_info(node)
            self._add_instance(node_id, addr, hostname, state_attributes, now_ts)
        LOG.info("ContainerCollector - Docker infrastructure components added.")

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
            self._update_instance(uuid, vcpus, mem, name, hostname, timestamp)
        elif event in ADD_EVENTS:
            self._add_instance(uuid, vcpus, mem, name, hostname, timestamp)

    def _get_instance_info(self, instance):
        """
        Extracts instance attributes.
        :param instance: Instance object.
        :return: # vcpus, memory size. name of instance, parent machine.
        """
        # TODO: define what we do and dont want in the state node
        attrs = {}
        desc = instance.attrs['Description']
        # flatten dict
        # TODO: may be nested deeper, recurse it!
        for key in desc.keys():
            if isinstance(desc[key], dict):
                sub_desc = desc[key]
                for skey in sub_desc.keys():
                    attrs[skey] = str(sub_desc[skey])
            else:
                attrs[key] = desc[key]
        return attrs

    # def _add_instance(self, uuid, vcpus, mem, name, hostname, timestamp):
    def _add_instance(self, uuid, address, hostname, state_attributes, timestamp):
        """
        Adds a new instance to the graph database.
        :param uuid: Instance id.
        :param vcpus: Number of vcpus.
        :param mem: Size of memory.
        :param name: Instance name.
        :param hostname: Parent host.
        :param timestamp: Epoch timestamp.
        """
        identity, state = self._create_instance_nodes(uuid, state_attributes)
        inst_node = self.graph_db.add_node(uuid, identity, state, timestamp)
        machine = self._get_machine_node(hostname)

        # Creates the edge between the instance and the machine.
        if inst_node is not None and machine is not None:
            self.graph_db.add_edge(inst_node, machine, timestamp, "HOSTS")

    def _update_instance(self, uuid, vcpus, mem, name, hostname, timestamp):
        """
        Updates an existing instance in the graph database.
        :param uuid: Instance id.
        :param vcpus: Number of vcpus.
        :param mem: Size of memory.
        :param name: Instance name.
        :param hostname: Parent host.
        :param timestamp: Epoch timestamp.
        """
        identity, state = self._create_instance_nodes(vcpus, mem, name)
        inst_node = self.graph_db.update_node(uuid, identity, state, timestamp)
        machine = self._get_machine_node(hostname)

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
    def _create_instance_nodes(uuid, state_attributes):
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
        state_node["node_name"] = 'state_name_temp'
        for key in state_attributes.keys():
            state_node[key] = state_attributes[key]

        return identity_node, state_node

    @staticmethod
    def get_connection_string(docker_conf):
        """
        Retrieves the Docker connection string.
        :param conf: Configuration Class.
        :return: Connection string.
        """
        connection_string = "tcp://{0}:{1}".format(
            docker_conf[1],
            docker_conf[0]
        )

        return connection_string

    @staticmethod
    def get_swarm_manager(docker_conf):
        """
        Retrieves Docker client object or error
        :return client object or error
        """
        # if docker_conf[2] and docker_conf[3]:
        #     tls_config = docker.tls.TLSConfig(
        #         client_cert=(docker_conf[2], docker_conf[3])
        #     )
        # else:
        #     tls_config = False
        #
        # manager_address = ContainerCollectorV1.get_connection_string(docker_conf)
        # client = docker.DockerClient(base_url=manager_address, tls=tls_config)
        client = docker.from_env()
        try:
            return client
        except KeyError as err:
            raise err

