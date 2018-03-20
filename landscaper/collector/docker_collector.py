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
Openstack docker collector class.
"""
import time
import docker

from landscaper.collector import base
from landscaper.common import LOG


# Node Structure.
IDEN_ATTR = {'layer': 'service', 'type': 'stack', 'category': 'compute'}
STATE_ATTR = {'stack_name': None, 'template': None}

ADD_EVENTS = ['docker.create', 'docker.start']
DELETE_EVENTS = ['docker.remove', 'docker.destroy']
UPDATE_EVENTS = ['docker.update']

CONFIG_SECTION = 'docker'

RELS = {'docker_container': 'HOSTS', 'container_task': 'DEPLOYED_BY',
        'task_service': 'OWNED_BY'}


class DockerCollectorV2(base.Collector):
    """
    Collects stacks running in heat and links them to instances in the graph
    database.
    """
    def __init__(self, graph_db, conf_manager, event_manager):
        events = ADD_EVENTS + UPDATE_EVENTS + DELETE_EVENTS
        super(DockerCollectorV2, self).__init__(graph_db, conf_manager,
                                                event_manager, events)
        self.graph_db = graph_db
        conf_manager.add_section(CONFIG_SECTION)
        docker_conf = conf_manager.get_swarm_info()
        self.swarm_manager = self.get_swarm_manager(docker_conf)

    @staticmethod
    def get_swarm_manager(docker_conf):
        """
        Return swarm manager.
        """
        if docker_conf[2] and docker_conf[3]:
            tls_config = docker.tls.TLSConfig(
                client_cert=(docker_conf[2], docker_conf[3])
            )
        else:
            tls_config = False
        url = DockerCollectorV2._get_connection_string(docker_conf)
        client = docker.Client(base_url=url, tls=tls_config)
        try:
            return client
        except KeyError as err:
            raise err

    def init_graph_db(self):
        """
        Adds stack nodes to the graph database and connects them to the
        stack's vms.
        """
        LOG.info("[DOCKER] Adding Docker components to the landscape.")
        now_ts = time.time()

        # add all containers
        for container in self.swarm_manager.containers():
            self._add_container(container, now_ts)

        # add all the stacks/services
        for service in self.swarm_manager.services():
            self._add_service(service, now_ts)

        # add all tasks connecting them to their docker nodes and containers
        for task in self.swarm_manager.tasks():
            self._add_task(task, now_ts)

    def update_graph_db(self, event, body):
        """
        Updates the heat elements in the graph database.
        :param event: The event that has occurred.
        :param body: The details of the event that occurred.
        """
        now_ts = time.time()
        uuid = body.get("Actor", dict()).get('ID', 'UNDEFINED')
        event_source = body.get("Type", None)
        LOG.info("[DOCKER] Processing event received: %s", event)
        LOG.info("SWARM-----UUID----- %s", uuid)
        try:
            if event in ADD_EVENTS:
                time.sleep(2)
                if body['Type'] == 'service':
                    stack = next((x for x in self.swarm_manager.services() if
                                  x['ID'] == uuid), None)
                    self._add_service(stack, now_ts)
                if body['Type'] == 'container':
                    if body['Action'] == 'create':
                        container = next(
                            (x for x in self.swarm_manager.containers() if
                             x['Id'] == uuid), None)
                        self._add_container(container, now_ts)
                    if body['Action'] == 'start':
                        task_id = body['Actor']['Attributes'][
                            'com.docker.swarm.task.id']
                        task = next((x for x in self.swarm_manager.tasks() if
                                     x['ID'] == task_id), None)
                        self._add_task(task, now_ts)
            elif event in DELETE_EVENTS:
                LOG.warn("SWARM: deleting stack:\n")
                if body['Type'] == 'container':
                    # delete the adjoining task
                    attrs = body['Actor']['Attributes']
                    if 'com.docker.swarm.task.id' in attrs:
                        task_id = attrs['com.docker.swarm.task.id']
                        self._delete_node(task_id, now_ts)
                self._delete_node(uuid, now_ts)
            elif event in UPDATE_EVENTS:
                if event_source == 'service':
                    stack = next((x for x in self.swarm_manager.services() if
                                  x['ID'] == uuid), None)
                    self._update_service(stack, now_ts)

        except docker.errors.NotFound:
            if event in ADD_EVENTS:
                LOG.warn("[SWARM] Missed stack into openstack\n EVENT:")
                LOG.warn(event)
                for service in self.swarm_manager.services.list():
                    LOG.warn("Stacks into heat openstack %s\n", service.id)
                LOG.warn("\n\n BODY:\n")
                LOG.warn(body)
                LOG.warn("SWARM: Stack with UUID %s not found", uuid)
            elif event in DELETE_EVENTS:
                LOG.warn("SWARM: deleting stack:\n")
                self._delete_node(uuid, now_ts)

    def _delete_node(self, uuid, timestamp):
        """
        Deletes the heat stack nodes from the database.
        :param uuid: Stack ID.
        :param timestamp: Time of deletion.
        """
        service_node = self.graph_db.get_node_by_uuid(uuid)
        if service_node:
            self.graph_db.delete_node(service_node, timestamp)

    def _add_service(self, service, timestamp):
        """
        Adds a Docker service node to the graph database.
        :param service: Docker Service object.
        :param timestamp: timestamp.
        """
        LOG.info("[DOCKER] Adding a service node the Graph")
        identity, state = self._create_docker_service_nodes(service)
        uuid = service["ID"]
        service_node = self.graph_db.add_node(uuid, identity, state, timestamp)
        LOG.warn(service_node)

    def _add_container(self, container, timestamp):
        """
        Adds a Docker container node to the graph database.
        :param container: Docker container object.
        :param timestamp: timestamp.
        """
        LOG.info("[DOCKER] Adding a container node the Graph")
        # get the info for the container
        container_info = self.swarm_manager.inspect_container(container['Id'])
        if container_info['State']['Running']:
            metadata = DockerCollectorV2.flatten_container_info(container_info)
            identity, state = self._create_docker_container_nodes(container,
                                                                  metadata)
            uuid = container["Id"]
            service_node = self.graph_db.add_node(uuid, identity, state,
                                                  timestamp)
            LOG.warn(service_node)
        LOG.warn('Skipping: Container not running {}'.format(container['Id']))

    def _add_task(self, task, timestamp):
        """
        Adds a Docker task node to the graph database.
        :param task: Docker task object.
        :param timestamp: timestamp.
        """
        LOG.info("[DOCKER] Adding a task node the Graph")
        if task['DesiredState'] == 'running':
            identity, state = self._create_docker_task_nodes(task)
            uuid = task["ID"]
            node_id = task["NodeID"]
            container_id = task["Status"]['ContainerStatus']['ContainerID']
            service_id = task["ServiceID"]
            task_node = self.graph_db.add_node(uuid, identity, state,
                                               timestamp)
            LOG.warn(task_node)
            if task_node is not None:
                docker_node = self.graph_db.get_node_by_uuid(node_id)
                container_node = self.graph_db.get_node_by_uuid(container_id)
                service_node = self.graph_db.get_node_by_uuid(service_id)
                if docker_node and container_node:
                    self.graph_db.add_edge(docker_node, container_node,
                                           timestamp, RELS['docker_container'])
                if container_node and task_node:
                    self.graph_db.add_edge(container_node, task_node,
                                           timestamp, RELS['container_task'])
                if task_node and service_node:
                    self.graph_db.add_edge(task_node, service_node, timestamp,
                                           RELS['task_service'])

    def _update_service(self, service, timestmp):
        """
        Manages an update to the docker service.
        :param service: Docker service object.
        :param timestmp: timestamp.
        """
        identity, state = self._create_docker_service_nodes(service)
        uuid = service['ID']

        # node will always be different and update unnecessarily
        self.graph_db.update_node(uuid, identity, state, timestmp)

    def _validate_docker(self):
        """
        Placeholder method for future integration with landscape validation
        :return:
        """
        try:
            containers = self.swarm_manager.containers()
            services = self.swarm_manager.services()
            tasks = self.swarm_manager.tasks()

            current_ids = {
                "docker_container": [x['Id'] for x in containers],
                "docker_service": [x['ID'] for x in services],
                "docker_task": [x['ID'] for x in tasks]
            }

            nodes = [x for x in self.swarm_manager.nodes() if
                     x.get("Status", {}).get('State') == 'ready']

            for node in nodes:
                node_id = node["ID"]
                node_sg = self.graph_db.get_subgraph(node_id, json_out=False)
                for node_id in node_sg.node:
                    d_type = node_sg.node[node_id]['type']
                    d_id = node_sg.node[node_id]['name']

                    if d_type in current_ids:
                        if d_id in current_ids[d_type]:
                            msg = 'updating: {} id: {}'.format(d_type, d_id)
                            LOG.info(msg)
                        else:
                            msg = '**deleting: {} id: {}'.format(d_type, d_id)
                            LOG.info(msg)
        except Exception as error:
            LOG.warn(error)

    def _create_docker_service_nodes(self, service):
        """
        Creates the identity and state nodes for a heat service.
        :param service: Docker service object.
        :return: Identity and state node.
        """
        identity = IDEN_ATTR.copy()
        identity['type'] = 'docker_service'
        state = STATE_ATTR.copy()
        service_name = service["Spec"]["Name"]
        LOG.warn("Creating service nodes for service: %s", service_name)
        state['service_name'] = service["Spec"]["Name"]
        state['template'] = service
        return identity, state

    def _create_docker_container_nodes(self, container, metadata):
        """
        Creates the identity and state nodes for an individual docker container
        :param container: docker container.
        :return: Identity and state node.
        """
        identity = IDEN_ATTR.copy()
        identity['type'] = 'docker_container'
        state = metadata.copy()
        LOG.warn("Creating container nodes for container: " + container["Id"])
        state['container_name'] = container["Names"][0].replace('/', '')
        state['template'] = container
        return identity, state

    def _create_docker_task_nodes(self, container):
        """
        Creates the identity and state nodes for an individual docker container
        :param container: docker container.
        :return: Identity and state node.
        """
        identity = IDEN_ATTR.copy()
        identity['type'] = 'docker_task'
        state = STATE_ATTR.copy()
        uuid = container["ID"]
        LOG.warn("Creating container nodes for container: " + container["ID"])
        state['service_id'] = container["ServiceID"]
        state['template'] = container['Spec']
        return identity, state

    def _get_resources(self, stack_id):
        """
        Finds the resources created in the heat template which are in the
        graph database.
        :param stack_id: Swarm stack id.
        :return: Graph database nodes associated with the heat stack.
        """
        nodes = list()
        service_tasks = [x for x in self.swarm_manager.tasks() if
                         x.get("ServiceID") == stack_id]
        for task in service_tasks:
            if not task["Status"].get("Err"):
                res_id = task["Status"]["ContainerStatus"]["ContainerID"]
                res_node = self.graph_db.get_node_by_uuid(res_id)
                if res_node is not None:
                    nodes.append(res_node)
        return nodes

    @staticmethod
    def flatten_container_info(c):
        """
        Take specifc nested keys/values in the docker info dictionary and
        flatten it to single level
        :param c: dictionary returned by docker inspect <container>
        :return: flattened dictionary
        """
        data = {}
        base_keys = ["Driver", "HostnamePath", "Mounts", "Name", "Platform",
                     "RestartCount"]
        config_keys = ["ExposedPorts", "Hostname", "Image", "User", "Volumes"]
        hconfig_keys = ["BlkioDeviceReadBps", "BlkioDeviceReadIOps",
                        "BlkioDeviceWriteBps", "BlkioDeviceWriteIOps",
                        "BlkioWeight", "BlkioWeightDevice", "CgroupParent",
                        "Cgroup", "CpuCount", "CpuPercent", "CpuPeriod",
                        "CpuQuota", "CpuShares", "CpusetCpus", "CpusetMems",
                        "DiskQuota", "DeviceCgroupRules", "IOMaximumBandwidth",
                        "IOMaximumIOps", "Isolation", "IpcMode", "Memory",
                        "MemoryReservation", "MemorySwap", "MemorySwappiness",
                        "NanoCpus", "NetworkMode", "PidMode", "PidsLimit",
                        "PortBindings", "ShmSize", "Ulimits", "VolumeDriver"]
        for k in base_keys:
            data[k] = c[k] if k in c else None
        for k in config_keys:
            data[k] = c['Config'][k] if k in c['Config'] else None
        for k in hconfig_keys:
            data[k] = c['HostConfig'][k] if k in c['HostConfig'] else None
        data['State'] = c['State']['Status']
        return data

    @staticmethod
    def _get_connection_string(docker_conf):
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
