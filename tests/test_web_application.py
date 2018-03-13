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
Tests for the REST API.
"""
import unittest
import logging
import random
import json
import time
import uuid
import mock
from mock import MagicMock

from landscaper.web import application
from landscaper.landscape_manager import LandscapeManager

from tests.test_utils import utils


class TestApplication(unittest.TestCase):
    """
    Tests for the REST API application.
    """

    def setUp(self):
        # Testing and api run in different directories.
        application.WORK_DIR = "."
        logging.disable(logging.CRITICAL)

        # Test flask calls.
        self.app = application.APP.test_client()

    def tearDown(self):
        logging.disable(logging.NOTSET)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_graph_success(self, mck_lm):
        """
        Test the success conditions for get_graph.
        """
        mock_graph = '{"1":2}'
        mock_get_graph = MagicMock(return_value=mock_graph)
        mck_lm.graph_db.get_graph = mock_get_graph

        response = self.app.get("/graph")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        self.assertTrue(self.is_json(response.get_data()))
        self.assertEqual(response.get_data(), mock_graph)
        mck_lm.graph_db.get_graph.assert_called_once_with()

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_subgraph_success(self, mck_lm):
        """
        Test the success conditions for get_subgraph.
        """
        base_url = "/subgraph/"
        node_id = "my_id"
        mock_graph = '{"a": 1}'
        mck_lm.graph_db.get_subgraph = MagicMock(return_value=mock_graph)

        response = self.app.get("{}{}".format(base_url, node_id))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(), mock_graph)
        self.assertEqual(response.mimetype, "application/json")
        mck_lm.graph_db.get_subgraph.assert_called_once_with(node_id,
                                                             timestmp=None,
                                                             timeframe=0)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_subgraph_failure(self, mock_lm):
        """
        Test the failure conditions for get_subgraph.
        """
        base_url = "/subgraph"
        node_id = self.random_uuid()
        url = "{}/{}".format(base_url, node_id)
        mock_lm.graph_db.get_subgraph = MagicMock(return_value=None)

        response = self.app.get(url)
        self.assertEqual(response.status_code, 400)
        actual_error_msg = self.get_error_message(response)
        err_msg = "Node with ID '{}', not in the landscape.".format(node_id)
        self.assertEqual(actual_error_msg, err_msg)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_subgraph_query_params(self, mck_lm):
        """
        Test the success conditions for get_subgraph with query parameters.
        """
        base_url = "/subgraph"
        node_id = "cache_1"
        t_stamp = str(int(time.time()))
        t_frame = "2"
        mock_graph = '{"type": "cache"}'
        full_url = "{}/{}?timestamp={}&timeframe={}".format(base_url,
                                                            node_id,
                                                            t_stamp,
                                                            t_frame)
        mck_lm.graph_db.get_subgraph = MagicMock(return_value=mock_graph)

        response = self.app.get(full_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(), mock_graph)
        mck_lm.graph_db.get_subgraph.assert_called_once_with(node_id,
                                                             timestmp=t_stamp,
                                                             timeframe=t_frame)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_node_by_uuid(self, mock_lm):
        """
        Test the success conditions for get_node_by_uuid.
        """
        base_url = "/node"
        node_id = self.random_uuid()
        url = "{}/{}".format(base_url, node_id)
        mck_g = '{"one":1, "two": 2}'
        mock_lm.graph_db.get_node_by_uuid_web = MagicMock(return_value=mck_g)
        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(), mck_g)
        self.assertEqual(response.mimetype, "application/json")
        mock_lm.graph_db.get_node_by_uuid_web.assert_called_once_with(node_id)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_node_by_uuid_failure(self, mock_lm):
        """
        Test the failure conditions for get_subgraph.
        """
        base_url = "/node"
        node_id = self.random_uuid()
        url = "{}/{}".format(base_url, node_id)
        mock_lm.graph_db.get_node_by_uuid_web = MagicMock(return_value=None)

        response = self.app.get(url)
        self.assertEqual(response.status_code, 400)
        actual_error_msg = self.get_error_message(response)
        err_msg = "Node with ID '{}', not in the landscape.".format(node_id)
        self.assertEqual(actual_error_msg, err_msg)

    @mock.patch("landscaper.web.application.time")
    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_node_by_props_success(self, mlm, mck_time):
        """
        Test the success conditions for get_node_by_properties.
        """
        base_url = "/nodes"
        params = [("layer", "virtual", "="), ("category", "compute"),
                  ("vcpu", 5, ">")]
        url = "{}?properties={}".format(base_url, params)
        time_s = 45

        # Mock Graph.
        graph = '{"graph": "name"}'
        mock_graph = MagicMock(return_value=graph)
        mlm.graph_db.get_node_by_properties_web = mock_graph

        # Mock time
        mck_time.time = MagicMock(return_value=time_s)

        # Call the application.
        response = self.app.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(), graph)
        self.assertEqual(response.mimetype, "application/json")
        mlm.graph_db.get_node_by_properties_web.assert_called_once_with(
            params, time_s, 0)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_node_by_props_failure(self, mock_lm):
        """
        Test the failure conditions for get_node_by_properties.
        """
        url = "/nodes"
        graph = '{"graph": "name"}'
        mock_lm.graph_db.get_node_by_properties = MagicMock(
            return_value=graph)

        response = self.app.get(url)

        self.assertEqual(response.status_code, 400)
        err_msg = self.get_error_message(response)
        self.assertEqual(err_msg, "Properties must be specified.")

    @staticmethod
    def is_json(json_str):
        """
        Return bool indicating if the string is json.
        """
        try:
            json.loads(json_str)
        except ValueError:
            return False
        return True

    @staticmethod
    def random_uuid():
        """
        Returns a random uuid.
        """
        nums = [1, 2, 3, 4, 5, 6, 7, 8]
        randhex = ''.join(str(random.choice(nums)) for i in range(32))
        return str(uuid.UUID(randhex))

    @staticmethod
    def get_error_message(response):
        """
        Strip out the error message from a HTTP Error response.
        """
        error_body = response.get_data().strip()
        start = error_body.index("<p>") + 3
        end = len(error_body) - 4
        return error_body[start:end]


class TestAddGeo(unittest.TestCase):
    """
    Tests for adding the geolocation to the node
    """

    def setUp(self):
        # Testing and api run in different directories.
        application.WORK_DIR = "."

        # Test flask calls.
        self.app = application.APP.test_client()

    def test_empty_list(self):
        """
        Test that it aborts with an empty list
        """
        url = "/coordinates"
        input_body = []
        response = self.app.put(url, data=input_body)

        self.assertEqual(response.status_code, 400)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_node_does_not_exist(self, mk_ls):
        """
        Test node does not exist in the Landscape
        """
        # 1. Replace DB connection with fake
        mk_ls.graph_db.update_node.return_value = (None, "")

        # 2. Create Fake Request
        fake_body = "[{'id': 'A', " \
                    "'geo': {'type': 'Point', 'coordinates': [1, 2],}}]"

        url = "/coordinates"
        response = self.app.put(url, data=fake_body)
        self.assertEqual(response.status_code, 400)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_node_exists(self, mk_ls):
        """
        Test two nodes are updated successfully
        """
        # 1. Replace DB connection with fake
        mk_ls.graph_db.update_node.return_value = ('Success', "")

        # mk_ls.graph_db.update_node.side_effect = None
        # 2. Create Fake Request
        fake_body = "[{'id': 'A', " \
                    "'geo': {'type': 'Point', 'coordinates': [1, 2],}}," \
                    "{'id': 'B', " \
                    "'geo': {'type': 'Polygon', 'coordinates': [5, 6],}}]"

        url = "/coordinates"
        response = self.app.put(url, data=fake_body)
        self.assertEqual(response.status_code, 200)
        call_count = mk_ls.graph_db.update_node.call_count
        self.assertEqual(call_count, 2)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_node_empty_list(self, mk_ls):
        """
        Test two nodes are updated successfully and third node is an empty list
        """
        # 1. Replace DB connection with fake
        mk_ls.graph_db.update_node.side_effect = [('Success', ""),
                                                  ('Success', ""),
                                                  (None, "")]
        # 2. Create Fake Request
        fake_body = "[{'id': 'A', " \
                    "'geo': {'type': 'Point', 'coordinates': [1, 2]}}," \
                    "{'id': 'B', " \
                    "'geo': {'type': 'Polygon', 'coordinates': [5, 6]}}," \
                    "{'id': 'C', " \
                    "'geo': {'type': 'Polygon', 'coordinates': [5, 6]}}]"

        url = "/coordinates"
        response = self.app.put(url, data=fake_body)
        self.assertEqual(response.status_code, 400)
        call_count = mk_ls.graph_db.update_node.call_count
        self.assertEqual(call_count, 3)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_partially_update_nodes(self, mk_ls):
        """
        Test two nodes are updated successfully
        One node is not in the Landscape and returns a None
        """
        # 1. Replace DB connection with fake
        mk_ls.graph_db.update_node.side_effect = [('Success', ""),
                                                  (None, ""),
                                                  ('Success', "")]

        # 2. Create Fake Request
        fake_body = "[{'id': 'A', " \
                    "'geo': {'type': 'Point', 'coordinates': [1, 2],}}," \
                    "{'id': 'B', " \
                    "'geo': {'type': 'Polygon', 'coordinates': [5, 6],}} ," \
                    "{'id': 'C', "\
                    "'geo': {'type': 'Polygon', 'coordinates': [5, 6],}}]"

        url = "/coordinates"
        response = self.app.put(url, data=fake_body)
        self.assertEqual(response.status_code, 400)
        call_count = mk_ls.graph_db.update_node.call_count
        self.assertEqual(call_count, 3)

    @mock.patch("landscaper.web.application.time")
    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_update_node_input(self, mk_ls, mk_time):
        """
        Test update node parameters correspond to Node_ID, timestamp and
        additional attributes containing the geolocation of the node
        """
        # 1. Replace DB connection with fake
        mk_time.time.return_value = 12
        mk_ls.graph_db.update_node.return_value = ('Success', "")

        # 2. Create Fake Request
        fake_body = "[{'id': 'A', " \
                    "'geo': {'type': 'Point', 'coordinates': [1, 2]}}]"

        url = "/coordinates"
        geo_string = json.dumps({'type': 'Point', 'coordinates': [1, 2]})
        geojson = {'geo': geo_string}
        response = self.app.put(url, data=fake_body)
        self.assertEqual(response.status_code, 200)
        mk_ls.graph_db.update_node.assert_called_once_with('A', 12,
                                                           extra_attrs=geojson)


class TestPutGeolocationIntegration(unittest.TestCase):
    """
    Integration tests for the put_geolocation method.
    """
    landscape_file = "tests/data/test_landscape_with_states.json"

    def setUp(self):
        utils.create_test_config()
        manager = LandscapeManager(utils.TEST_CONFIG_FILE)
        self.graph_db = manager.graph_db
        self.graph_db.delete_all()
        self.graph_db.load_test_landscape(self.landscape_file)

        # Test flask calls.
        self.app = application.APP.test_client()
        application.initilise_application()

    def tearDown(self):
        self.graph_db.delete_all()
        utils.remove_test_config()

    def test_node_update_geo_exists(self):
        """
        Test that after update is called a geo is added to the node.
        """
        node_id = 'nova-1'
        old_node = self._node_state_attributes(node_id)

        # Create fake body with geolocation for node
        fake_body = "[{'id': '%s', 'geo': {'type': 'Point', " \
                    "'coordinates': [1, 2]}}]" % node_id

        url = "/coordinates"
        response = self.app.put(url, data=fake_body)

        # Get node again, hopefully with geo.
        new_node = self._node_state_attributes(node_id)

        self.assertEqual(response.status_code, 200)
        self.assertFalse('geo' in old_node)
        self.assertTrue('geo' in new_node)

    def test_node_update_geo_not_exist(self):
        """
        Test if a node does not exist, it returns an error.
        """
        node_id = 'fake_node'
        old_node = self._node_state_attributes(node_id)
        # Create fake body for fake node with geolocation
        fake_body = "[{'id': '%s', 'geo': {'type': 'Point', " \
                    "'coordinates': [1, 2]}}]" % node_id
        url = "/coordinates"
        response = self.app.put(url, data=fake_body)

        self.assertFalse(old_node)
        self.assertEqual(response.status_code, 400)

    def _node_state_attributes(self, node_id):
        """
        returns a node from the landscape by id.
        :param node_id: The node to grab.
        :return: a node from the landscape by id.
        """
        graph = self.graph_db.get_node_by_uuid_web(node_id, json_out=False)
        if graph:
            return graph.nodes(data=True)[0][1]['attributes']

        return None
