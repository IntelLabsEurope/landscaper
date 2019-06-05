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
Utilities used for testing.
"""

import unittest
import mock
import os
from tests.test_utils import utils
from landscaper.utilities import configuration, cimi

CONFIGURATION_SECTION = 'general'
CONFIGURATION_VARIABLE = 'cimi_url'
CONFIGURATION_VALUE = 'http://localhost'


def mocked_requests_post(*args, **kwargs):
    print args

    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    if args[0] == 'http://localhost/service-container-metric':
        return MockResponse({"status": "OK"}, 200)
    return MockResponse(None, 404)


def mocked_requests_put(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data
    print args

    if args[0] == 'http://localhost/service-container-metric/e2344324':
        return MockResponse({"status": "OK"}, 200)
    return MockResponse(None, 404)


class TestCimi(unittest.TestCase):
    """
    Unit tests for hwloc and cpuinfo retireval from DataClay.
    """

    @classmethod
    def setUpClass(cls):
        utils.create_test_config()

    @classmethod
    def tearDownClass(cls):
        utils.remove_test_config()

    def setUp(self):
        test_config = "tests/data/tmp_config.conf"
        self.conf_manager = configuration.ConfigurationManager(test_config)
        self.conf_manager.add_section(CONFIGURATION_SECTION)
        self.conf_manager.set_variable(
            CONFIGURATION_SECTION, CONFIGURATION_VARIABLE, CONFIGURATION_VALUE)
        self.cimi_client = cimi.CimiClient(self.conf_manager)
        collection_item = {
            "id": "e2344324", "device_id": "YQCJB3SD2A9A", "container_id": "e2344324"}
        collection = {'ServiceContainerMetrics': [collection_item]}
        self.cimi_client.get_collection = mock.MagicMock(
            return_value=collection)

    @mock.patch('requests.post', side_effect=mocked_requests_post)
    def test_add_service_container_metric(self, mock_post):
        id = "e2344324"
        device_id = "YQCJB3SD2A9A"
        start_time = "1559765182"
        response = self.cimi_client.add_service_container_metrics(
            id, device_id, start_time)
        self.assertEqual(response.status_code, 200, "Status code not 200")

    @mock.patch('requests.put', side_effect=mocked_requests_put)
    def test_update_service_container_metrics(self, mock_post):
        id = "e2344324"
        device_id = "YQCJB3SD2A9A"
        end_time = "1559765182"
        response = self.cimi_client.update_service_container_metrics(
            id, device_id, end_time)
        print response.status_code
        self.assertEqual(response.status_code, 200, "Status code not 200")
