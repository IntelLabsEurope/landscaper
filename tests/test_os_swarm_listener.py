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
Tests for the Docker Swarm Listener
"""
import unittest
import mock
import json
import docker
import requests
from landscaper.event_listener import os_swarm_listener as OS_listener
from landscaper.event_listener.os_swarm_listener import OSSwarmListener
from landscaper.utilities import configuration as config
from landscaper.event_listener import base
from landscaper.common import LOG


class TestOSSwarmListener(unittest.TestCase):
    listener_module = "landscaper.event_listener.os_swarm_listener"

    def setUp(self):
        # Mock up the configuration for the Listener.
        attr = {'get_swarm_info.return_value': self._swarm_conf()}
        mck_conf = mock.Mock(spec_set=config.ConfigurationManager, **attr)

        self.listener = OSSwarmListener(mock.Mock(), mck_conf)
        self.mck_conf = mck_conf

    def test_connection_string_building(self):
        """
        Ensure that the connection string builds using the config variables.
        """
        connection_string = OSSwarmListener._get_connection_string(
            [2377, 'localhost'])

        # Check the string
        expected_conn_str = 'tcp://localhost:2377'
        self.assertEqual(connection_string, expected_conn_str)

    @staticmethod
    def _swarm_conf():
        """
        Fake configuration values for the Swarm listener.
        :return:  configuration as a named tuple.
        """
        conf = (2377, 'localhost')
        return conf

    def test_events_dispatched(self):
        """
        Test that events received are dispatched.
        """
        OS_listener.EVENTS = ['event_1', 'event_2', 'event_3', 'event_4']
        emanager_mck = mock.Mock()
        listener = OSSwarmListener(emanager_mck, self.mck_conf)
        listener._get_client = mock.MagicMock()

        emanager_mck.dispatch_event.assert_not_called()
        e = ['event_2', 'event_4']
        for event in self._test_events(e):
            name = e.pop(0)
            listener._cb_event(event)
            emanager_mck.dispatch_event.assert_called_once_with(
                name, json.loads(event))
            emanager_mck.reset_mock()

    def test_inheritance(self):
        """
        Ensure that the event listener base class is needed, because methods
        from the base class are used in the dispatcher.
        """
        self.assertIsInstance(self.listener, base.EventListener)

    def test_events_not_dispatched(self):
        """
        Check that unknown events are not dispatched.
        """
        OS_listener.EVENTS = ['eventA', 'eventB', 'eventC']
        emanager_mck = mock.Mock()
        listener = OSSwarmListener(emanager_mck, self.mck_conf)
        listener._get_client = mock.MagicMock()

        emanager_mck.dispatch_event.assert_not_called()
        for event in self._test_events(['eventX', 'eventY', 'eventZ']):
            listener._cb_event(event)
        emanager_mck.dispatch_event.assert_not_called()

    @staticmethod
    def _test_events(event_names):
        """
        Generate some events in the form expected by the callback.
        :param event_names: List of event names.
        :return: List of events.
        """
        events = []
        for event_name in event_names:
            event = {}
            event['Action'] = event_name
            event['Type'] = ""
            event = json.dumps(event)
            events.append(event)
        return events

    def test_get_client_no_tls_failure_not_existing_service(self):
        """
        Tests if a Docker client is returned
        :return:
        """
        emanager_mck = mock.Mock()
        listener = OSSwarmListener(emanager_mck, self.mck_conf)
        listener._get_client = mock.MagicMock(side_effect=SystemExit)
        try:
            client = listener._get_client()
        except SystemExit:
            assert(True)


if __name__ == '__main__':
    unittest.main()
