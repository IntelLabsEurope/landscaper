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
Openstack rabbitMQ listener.
"""
import time

from kombu import Connection, Exchange, Queue, Consumer
from landscaper.common import LOG
from landscaper.event_listener import base

# Events which this listener accepts.
EVENTS = [
    'compute.instance.create.start',
    'compute.instance.create.end', 'compute.instance.resize.revert.end',
    'compute.instance.finish_resize.end', 'compute.instance.rebuild.end',
    'compute.instance.update', 'compute.instance.exists',
    'compute.instance.delete.end', 'orchestration.stack.create.end',
    'orchestration.stack.update.end', 'orchestration.stack.resume.end',
    'orchestration.stack.suspend.end', 'orchestration.stack.delete.end',
    'network.create.end', 'network.update.end', 'network.delete.end',
    'subnet.create.end', 'subnet.update.end', 'subnet.delete.end',
    'port.create.end', 'port.update.end', 'router.interface.create',
    'port.delete.end', 'router.interface.delete', 'volume.create.end',
    'volume.update.end', 'volume.resize.end', 'volume.attach.end',
    'volume.detach.end', 'volume.delete.end', 'volume.attach.start',
    'compute.instance.shutdown.end', 'compute.instance.volume.attach',
    'orchestration.stack.create.start']

CONFIG_SECTION = 'rabbitmq'


class OSRabbitMQListener(base.EventListener):
    """
    Listener implementation for the openstack Rabbit MQ.
    """
    def __init__(self, events_manager, conf):
        super(OSRabbitMQListener, self).__init__(events_manager)
        self.register_events(EVENTS)

        # Grab rabbit configuration data.
        conf.add_section(CONFIG_SECTION)
        rabbit_conf = conf.get_rabbitmq_info()
        self.topic = rabbit_conf[4]
        self.queue = rabbit_conf[5]
        self.exchanges = rabbit_conf[6]
        self.connection_string = self._get_connection_string(rabbit_conf)

    @staticmethod
    def create_exchange(exchange_name):
        """
        Creates exchange for amqp notifications
        """
        return Exchange(exchange_name, type='topic', durable=True)

    @staticmethod
    def create_queue(topic_name, exchange):
        """
        Creates Queue for amqp notifications
        """
        return Queue(topic_name, exchange=exchange,
                     durable=True, routing_key=topic_name)

    def listen_for_events(self):
        """
        Listen for events coming from the openstack notification queue.
        """
        self._consume_notifications()
        time.sleep(5)

    @staticmethod
    def _create_exchange(topic_name):
        return Exchange(topic_name, type='topic', durable=True)

    @staticmethod
    def _create_queue(topic, exchange):
        return Queue(topic, exchange=exchange, durable=True, routing_key=topic)

    def _consume_notifications(self):
        """
        Consume notification from Openstack notification queue.
        """
        LOG.info("Attempting to connect to address: %s",
                 self.connection_string)
        with Connection(self.connection_string) as conn:
            consumer = Consumer(conn, callbacks=[self._cb_event])
            for exchange_name in self.exchanges:
                exchange = OSRabbitMQListener.create_exchange(exchange_name)
                queue = OSRabbitMQListener.create_queue(self.topic, exchange)
                consumer.add_queue(queue)
            with consumer:
                LOG.info("Connected to address: %s", self.connection_string)
                while True:
                    conn.drain_events()
        return

    def _cb_event(self, body, message):
        """
        Callback which is automatically called when an event is received on the
        notification queue. It dispatches the event to the registered handler.
        """
        try:
            event = body['event_type']
            LOG.info("event: %s", event)
            if event in EVENTS:
                self.events_manager.dispatch_event(event, body)
            message.ack()
        except TypeError:
            pass

    @staticmethod
    def _get_connection_string(rabbit_conf):
        """
        Retrieves the rabbit MQ connection string.
        :param rabbit_conf: Configuration Class.
        :return: Connection string.
        """
        connection_string = "amqp://{}:{}@{}:{}/%2F".format(rabbit_conf[0],
                                                            rabbit_conf[1],
                                                            rabbit_conf[2],
                                                            rabbit_conf[3])
        return connection_string
