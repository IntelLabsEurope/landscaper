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
Edge Cask listener.
"""
import time

import docker
import json
import requests
from landscaper.common import LOG
from landscaper.event_listener import base

CONFIG_SECTION = 'docker'

EVENTS = [
    'docker.create',
    'docker.start',
    'docker.remove',
    'docker.destroy',
    'docker.update',
    'dockerhost.create',
    'dockerhost.remove',
    'dockerhost.update'
]


class OSSwarmListener(base.EventListener):
    """
    Listener implementation for the Docker protocol
    """

    def __init__(self, events_manager, conf):
        super(OSSwarmListener, self).__init__(events_manager)
        self.register_events(EVENTS)
        # Grab docker configuration data.
        conf.add_section(CONFIG_SECTION)
        self.docker_conf = conf.get_swarm_info()
        self.connection_string = OSSwarmListener._get_connection_string(
            self.docker_conf)

    def listen_for_events(self):
        """
        Listen for events coming from the openstack notification queue.
        """
        self._consume_notifications()
        time.sleep(5)

    def _consume_notifications(self):
        """
        Consume notification from Swarm notification queue.
        """
        LOG.info("Subscribing to Docker events...")
        client = self._get_leader_client()

        for event in client.events():
            LOG.info(event)
            self._cb_event(event)

        return

    def _get_leader_client(self):
        """
        Returns the Docker client relative to the manager into the Swarm.
        :return: the Docker client relative to the manager.
        """
        client = self._get_client()
        nodes = client.nodes.list(filters={'role': 'manager'})
        if nodes:
            if client.info()["Swarm"]["NodeID"] == nodes[0].attrs["ID"]:
                return client
            else:
                self.docker_conf[1] = nodes[0].attrs["Status"]["Addr"]
                return docker.DockerClient(
                    base_url=OSSwarmListener._get_connection_string()
                )

    def _get_client(self):
        """
        Returns a Docker client accordingly to the configuration file
        :return: Docker client
        """
        # if len(self.docker_conf) > 2 and \
        #         self.docker_conf[2] and self.docker_conf[3]:
        #     tls_config = docker.tls.TLSConfig(
        #         client_cert=(self.docker_conf[2], self.docker_conf[3])
        #     )
        # else:
        #     tls_config = False
        try:
        #     client = docker.DockerClient(
        #         base_url=OSSwarmListener._get_connection_string(self.docker_conf),
        #         tls=tls_config
        #     )
            client = docker.from_env()
            return client
        except requests.ConnectionError as e:
            LOG.error('Please check Configuration file or Service availability')
            LOG.error(e.message)
            exit()

    def _cb_event(self, body):
        """
        Callback which is automatically called when an event is received on the
        notification queue. It dispatches the event to the registered handler.
        """
        dockerhost_event_types = ['node']
        docker_event_types = ['service', 'task', 'container']

        try:
            body_json = json.loads(body)
            event = body_json['Action']
            event_type = body_json['Type']
            if event_type in docker_event_types:
                event = 'docker.{}'.format(event)
            elif event in dockerhost_event_types:
                event = 'dockerhost.{}'.format(event)
            LOG.info("event: %s", event)
            if event in EVENTS:
                self.events_manager.dispatch_event(event, body_json)
        except TypeError:
            pass

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
