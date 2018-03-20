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
""""
Tests for the openstack messaging queue.
"""
from collections import namedtuple
import unittest
import mock
import kombu

from landscaper.event_listener import os_rabbitmq_listener as OS_listener
from landscaper.event_listener import base
from landscaper.utilities import configuration as config

from tests.test_utils import utils

# pylint: disable=W0212


class TestOSMQueueConsumer(unittest.TestCase):
    """
    Test the OSMQueueConsumer class.
    """
    @mock.patch("landscaper.event_listener.os_rabbitmq_listener.LOG")
    def test_failed_connection_logged(self, mck_log):
        """
        The on_connection_error method is called when there is a failed
        connection. The reconnection is taken care of by the ConsumerMixin,
        we just ensure that this failed connection was logged.
        """
        consumer = OS_listener.OSMQueueConsumer(None, None, None)

        mck_log.warning.assert_not_called()
        consumer.on_connection_error("", "")
        self.assertEqual(mck_log.warning.call_count, 1)

    @mock.patch("landscaper.event_listener.os_rabbitmq_listener.LOG")
    def test_connection_revived_logged(self, mck_log):
        """
        The on_connection_revived method is called after a connection has been
        revived. Ensure that this is logged.
        """
        consumer = OS_listener.OSMQueueConsumer(mock.Mock(), None, None)

        mck_log.info.assert_not_called()
        consumer.on_connection_revived()
        self.assertEqual(mck_log.info.call_count, 1)

    @staticmethod
    def test_consumer_instantiated():
        """
        Ensure that the consumer is instantiated with the correct queues and
        callback.
        """
        queues = [2, 4, 6]
        callback = "callback"
        consumer = OS_listener.OSMQueueConsumer(mock.Mock(), queues, callback)

        k_consumer = mock.Mock()    # Mock the Kombu consumer.
        consumer.get_consumers(k_consumer, None)
        k_consumer.assert_called_once_with(queues=queues, callbacks=[callback])


class TestOpenstackEventListener(unittest.TestCase):
    """
    Test openstack event listener
    """
    listener_module = "landscaper.event_listener.os_rabbitmq_listener"

    def setUp(self):
        # Mock up the configuration for the Listener.
        attr = {'get_rabbitmq_info.return_value': self._rabbit_conf()}
        mck_conf = mock.Mock(spec_set=config.ConfigurationManager, **attr)

        self.listener = OS_listener.OSRabbitMQListener(mock.Mock(), mck_conf)
        self.mck_conf = mck_conf

    def test_connection_string_building(self):
        """
        Ensure that the connection string builds using the config variables.
        """
        connection_string = self.listener._get_connection_string()

        # Check the string
        expected_conn_str = 'amqp://name:abc@server1:5555/%2F'
        self.assertEqual(connection_string, expected_conn_str)

    def test_inheritance(self):
        """
        Ensure that the event listener base class is needed, because methods
        from the base class are used in the dispatcher.
        """
        self.assertIsInstance(self.listener, base.EventListener)

    def test_queues_for_exchanges(self):
        """
        Ensure that each exchange is connected to a queue.
        """
        queues = self.listener._queues()

        exchanges = [queue.exchange.name for queue in queues]
        conf_exchanges = self.mck_conf.get_rabbitmq_info().exchanges

        self.assertEqual(exchanges, conf_exchanges)

    def test_queue_topics(self):
        """
        Ensure we use the topic from the OS confs as a routing key.
        """
        conf_topic = self.mck_conf.get_rabbitmq_info().topic

        queues = self.listener._queues()
        topics = [queue.routing_key for queue in queues]

        self.assertEqual(topics, [conf_topic]*len(topics))

    def test_correct_queue_name(self):
        """
        Queue is named correctly.
        """
        conf_name = self.mck_conf.get_rabbitmq_info().queue

        queues = self.listener._queues()
        topics = [queue.name for queue in queues]

        self.assertEqual(topics, [conf_name]*len(topics))

    def test_messages_acknowledged(self):
        """
        All messages should be acknowledged so that they are removed from the
        queue once spotted.
        """
        OS_listener.EVENTS = ['event_1', 'event_2', 'event_3', 'event_4']

        # Events for the callback
        test_events = self._test_events(['event_2', 'event_3', 'event_8'])

        message_mock = mock.Mock()
        for event in test_events:
            self.listener._cb_event(event, message_mock)
            message_mock.ack.assert_called_once_with()
            message_mock.reset_mock()

    def test_events_dispatched(self):
        """
        Test that events received are dispatched.
        """
        OS_listener.EVENTS = ['event_1', 'event_2', 'event_3', 'event_4']
        emanager_mck = mock.Mock()
        listener = OS_listener.OSRabbitMQListener(emanager_mck, self.mck_conf)

        emanager_mck.dispatch_event.assert_not_called()
        for event in self._test_events(['event_2', 'event_4']):
            name = event['event_type']
            listener._cb_event(event, mock.Mock())
            emanager_mck.dispatch_event.assert_called_once_with(name, event)
            emanager_mck.reset_mock()

    def test_events_not_dispatched(self):
        """
        Check that unknown events are not dispatched.
        """
        OS_listener.EVENTS = ['eventA', 'eventB', 'eventC']
        emanager_mck = mock.Mock()
        listener = OS_listener.OSRabbitMQListener(emanager_mck, self.mck_conf)

        emanager_mck.dispatch_event.assert_not_called()
        for event in self._test_events(['eventX', 'eventY', 'eventZ']):
            listener._cb_event(event, mock.Mock())
        emanager_mck.dispatch_event.assert_not_called()

    @mock.patch.object(OS_listener.OSMQueueConsumer, 'run')
    def test_consumer_started(self, mck_consumer_run):
        """
        Check that the consumer is run after a call to the listen_for_events
        method.
        """
        self.listener.listen_for_events()
        mck_consumer_run.assert_called_once_with()

    @mock.patch(listener_module + ".OSMQueueConsumer")
    def test_stuff(self, mck_consumer):
        """
        Check that the consumer is being loaded correctly.
        """
        self.listener.listen_for_events()
        initial_parameters = mck_consumer.call_args_list[0][0]

        self.assertIsInstance(initial_parameters[0], kombu.Connection)
        self.assertGreater(len(initial_parameters[1]), 0)
        self.assertEqual(initial_parameters[2], self.listener._cb_event)

        for queue in initial_parameters[1]:
            self.assertIsInstance(queue, kombu.Queue)

    @staticmethod
    def _test_events(event_names):
        """
        Generate some events in the form expected by the callback.
        :param event_names: List of event names.
        :return: List of events.
        """
        events = []
        for event_name in event_names:
            event = {'event_type': event_name}
            event[utils.random_string(5)] = utils.random_string(8)
            events.append(event)
        return events

    @staticmethod
    def _rabbit_conf():
        """
        Fake configuration values for the openstack rabbitMQ listener.
        :return:  configuration as a named tuple.
        """
        rabbit = namedtuple("rabbitMQ", 'username password host port topic '
                                        'queue exchanges')
        exchanges = ['north', 'east', 'south', 'west']
        conf = rabbit('name', 'abc', 'server1', '5555', 'tinsel', 'cities',
                      exchanges)
        return conf
