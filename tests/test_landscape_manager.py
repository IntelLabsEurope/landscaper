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
Landscape Manager Class tests.
"""
import unittest
import mock

from landscaper import landscape_manager

# W0212 -  Access to a protected member
# pylint: disable=W0212


class TestLandscapeManger(unittest.TestCase):
    """
    Unit tests for the landscape manager.
    """
    def setUp(self):
        self.landscape_mgr = landscape_manager.LandscapeManager()
        self.listener_1 = mock.Mock()
        self.listener_2 = mock.Mock()
        self.landscape_mgr.listeners = [self.listener_1, self.listener_2]

    def test_listeners_started(self):
        """
        Ensure all listeners get started.
        """
        self.landscape_mgr._start_listeners()

        # Listeners are started.
        self.listener_1.start.assert_called_once_with()
        self.listener_2.start.assert_called_once_with()

    def test_threads_joined(self):
        """
        Ensure all listeners are joined so that the threads do not fall out.
        """
        self.landscape_mgr._start_listeners()

        # Listeners are joined.
        self.listener_1.join.assert_called_once_with()
        self.listener_2.join.assert_called_once_with()
