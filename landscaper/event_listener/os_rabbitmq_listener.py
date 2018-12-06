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
from kombu import Connection, Queue, Exchange
from kombu.mixins import ConsumerMixin
from kombu import exceptions

from landscaper.event_listener import base
from landscaper.common import LOG

EVENTS = [
    'compute.instance.create.start', 'orchestration.stack.create.start',
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
    'compute.instance.shutdown.end', 'compute.instance.volume.attach']

CONFIG_SECTION = 'rabbitmq'
CONNECTION_RETRIES = 10         # Number of retries after a broken connection.


class OSRabbitMQListener(base.EventListener):
    """
    Listener implementation for the openstack Rabbit MQ.
    """
    def __init__(self, events_manager, conf):
        super(OSRabbitMQListener, self).__init__(events_manager)
        self.register_events(EVENTS)

        # Grab rabbit configuration data.
        conf.add_section(CONFIG_SECTION)
        self.rbq = conf.get_rabbitmq_info()
        self.connection_string = self._get_connection_string()

    def listen_for_events(self):
        """
        Entry point for the child event listener.
        """
        msg = "Connecting to Openstack message queue at address: %s."
        with Connection(self.connection_string) as conn:
            consumer = OSMQueueConsumer(conn, self._queues(), self._cb_event)
            try:
                LOG.info(msg, self.connection_string)
                consumer.run()
            except exceptions.KombuError as exc:
                LOG.error(exc, exc_info=1)

    def _queues(self):
        """
        Build the listener queue and redirect exchange output to this queue.
        :return: List of queues.
        """
        queues = []
        for exchange_name in self.rbq.exchanges:
            exchange = Exchange(exchange_name, type='topic')
            queue = Queue(self.rbq.queue, exchange, self.rbq.topic)
            queues.append(queue)
        return queues

    def _get_connection_string(self):
        """
        Retrieves the rabbit MQ connection string.
        :param rabbit_conf: Configuration Class.
        :return: Connection string.
        """
        connection_string = "amqp://{}:{}@{}:{}/%2F".format(self.rbq.username,
                                                            self.rbq.password,
                                                            self.rbq.host,
                                                            self.rbq.port)
        return connection_string

    def _cb_event(self, body, message):
        """
        Callback which is automatically called when an event is received on the
        notification queue. It dispatches the event to the registered handler.
        """
        try:
            event = body['event_type']
            LOG.info("event: %s", event)
            #LOG.info("Event Data: %s", body)
            if event in EVENTS:
                self.events_manager.dispatch_event(event, body)
            message.ack()
        except TypeError:
            pass


class OSMQueueConsumer(ConsumerMixin):
    """
    Open stack message queue consumer.
    """
    def __init__(self, connection, queues, callback):
        self.connection = connection
        self.queues = queues
        self.callback = callback
        self.connect_max_retries = CONNECTION_RETRIES
        self.retry_tracker = 0

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=self.queues, callbacks=[self.callback])]

    def on_connection_error(self, exc, interval):
        """
        Method called when there is a connection problem.
        :param exc: The connection exception.
        :param interval: The interval until the next reconnect attempt is made.
        """
        super(OSMQueueConsumer, self).on_connection_error(exc, interval)
        self.retry_tracker += 1
        err_msg = "Broker connection error: %s. Attempting reconnect " \
                  "(%s/%s) in %ss."
        LOG.warning(err_msg, exc, self.retry_tracker, self.connect_max_retries,
                    interval)

    def on_connection_revived(self):
        """
        Method called when a connection to the broker is successfully made.
        """
        super(OSMQueueConsumer, self).on_connection_revived()
        self.retry_tracker = 0
        info_msg = "Connected to Openstack message queue at address: %s."
        LOG.info(info_msg, self.connection.as_uri())
