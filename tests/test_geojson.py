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
Tests for GeoJSON retrieval
"""
import json
import time
import unittest
import mock

from networkx.readwrite import json_graph

from landscaper import landscape_manager
from landscaper.utilities.coordinates import Geo
from landscaper.web import application

from tests.test_utils import utils

IDENTITY_ATTR = {'layer': 'virtual', 'type': 'vm', 'category': 'compute'}
STATE_ATTR = {'vcpu': None, 'mem': None}


class TestGeoJSONJson(unittest.TestCase):
    """
    Unit tests for the GeoJSON retrieval.
    """
    landscape_file = "tests/data/test_landscape_with_states.json"

    @classmethod
    def setUpClass(cls):
        """
        These tests connect to a running graph database and so for safety
        reasons this needs to be explicitly set.
        """
        utils.create_test_config()

    @classmethod
    def tearDownClass(cls):
        utils.remove_test_config()

    def setUp(self):
        self.identity = IDENTITY_ATTR.copy()
        self.state = STATE_ATTR.copy()
        manager = landscape_manager.LandscapeManager(utils.TEST_CONFIG_FILE)

        # Set the application landscape manager to the test manager.
        application.LANDSCAPE = manager

        # Prepare the database
        self.graph_db = manager.graph_db
        self.graph_db.delete_all()
        self.app = application.APP.test_client()

    def tearDown(self):
        self.graph_db.delete_all()

    def test_geo_decorator(self):
        """
        Test that the geo decorator returns a correctly formatted
        FeatureCollection.
        """
        test_graph = _test_graph()
        geo = Geo.extract_geo(json.dumps(test_graph))
        geo = json.loads(geo)
        self.assertEquals(geo["type"], "FeatureCollection")
        self.assertEquals(type(geo["features"]), list)
        self.assertEquals(len(geo["features"]), 2)

    # tests that the regular graph method works without URL query parameter geo=True
    def test_graph_without_feature_collection(self):
        self.insert_nodes()
        base_url = "/graph"
        response = self.app.get("{}".format(base_url))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        resp = response.get_data()
        response = json.loads(resp)
        self.assertFalse("type" in "response")
        self.assertTrue("graph" in response)

    def test_feature_collection_graph(self):
        """
        Graph success test.
        """
        self.insert_nodes()
        base_url = "/graph?geo=True"
        response = self.app.get("{}".format(base_url))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        geos = response.get_data()
        geo = json.loads(geos)

        self.assertEquals(geo["type"], "FeatureCollection")
        self.assertEquals(type(geo["features"]), list)
        self.assertEquals(len(geo["features"]), 2)

    def test_feature_coll_subgraph(self):
        """
        subgraph success test.
        """
        self.insert_nodes()
        base_url = "/subgraph/"
        node_id = "nodey1"
        response = self.app.get("{}{}?geo=True".format(base_url, node_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        geos = response.get_data()
        geo = json.loads(geos)
        self.assertEquals(geo["type"], "FeatureCollection")
        self.assertEquals(type(geo["features"]), list)
        self.assertEquals(len(geo["features"]), 1)

    def test_feature_collection_node(self):
        """
        Covers implementation ILX-41 and unit test ILX-47
        """
        self.insert_nodes()
        base_url = "/node/"
        node_id = "nodey1"
        response = self.app.get("{}{}?geo=True".format(base_url, node_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/json")
        geos = response.get_data()
        geo = json.loads(geos)
        self.assertEquals(geo["type"], "FeatureCollection")
        self.assertEquals(type(geo["features"]), list)
        self.assertEquals(len(geo["features"]), 1)

    def insert_nodes(self):
        """
        Push nodes to the database.
        """
        self.graph_db.delete_all()
        geom1 = {"type": "Point", "coordinates": [102.0, 0.5]}
        geom2 = {"type": "Point", "coordinates": [10.0, 1.5]}
        timestamp = int(time.time())

        state1 = self.state.copy()
        state1['geo'] = geom1
        state2 = self.state.copy()
        state2['geo'] = geom2

        self.graph_db.add_node("nodey1", IDENTITY_ATTR, state1, timestamp)
        self.graph_db.add_node("nodey2", IDENTITY_ATTR, state2, timestamp)


def _test_graph():
    """
    Simple test graph.
    """
    graph = {'directed': True, 'graph': {}, 'nodes': [
        {u'category': u'compute', u'layer': u'virtual', u'name': u'nodey1',
         'attributes': {
             u'geo': u'{"type": "Point",' u' "coordinates": [102.0, 0.5]}'},
         u'type': u'vm', 'id': u'nodey1'},
        {u'category': u'compute', u'layer': u'virtual', u'name': u'nodey2',
         'attributes': {
             u'geo': u'{"type": "Point", "coordinates": [10.0, 1.5]}'},
         u'type': u'vm', 'id': u'nodey2'}], 'links': [], 'multigraph': False}
    return graph


class TestBoolean(unittest.TestCase):
    """
    Tests for the _boolean method
    """

    def test_bool_types(self):
        """
        Test that the method can handle bool types.
        """
        bool_true = application._boolean(True)
        bool_false = application._boolean(False)

        self.assertIsInstance(bool_true, bool)
        self.assertIsInstance(bool_false, bool)
        self.assertTrue(bool_true)
        self.assertFalse(bool_false)

    def test_one_zero(self):
        """
        Test that one and zero are interpreted correctly.
        """
        one = application._boolean(1)
        zero = application._boolean(0)

        self.assertIsInstance(one, bool)
        self.assertIsInstance(zero, bool)
        self.assertTrue(one)
        self.assertFalse(zero)

    def test_none_false(self):
        """
        Test that None is interpreted as false.
        """
        self.assertFalse(application._boolean(None))

    def test_strings_success(self):
        """
        Test that various strings for success.
        """
        for str_truth_val in ['true', 'TRUE', ' True ', '1', '1 ']:
            bool_true = application._boolean(str_truth_val)
            self.assertIsInstance(bool_true, bool)
            self.assertTrue(bool_true)

        for str_false_val in ['FALSE', 'false', ' False', '0', ' 0 ']:
            bool_false = application._boolean(str_false_val)
            self.assertIsInstance(bool_false, bool)
            self.assertFalse(bool_false)

    def test_strings_failure(self):
        """
        All bad strings.
        """
        for str_fail in ['123', 'Tr ue', '00', 'mario', '']:
            bool_false = application._boolean(str_fail)
            self.assertIsInstance(bool_false, bool)
            self.assertFalse(bool_false)

    def test_somethingelse(self):
        """
        Just some object
        """
        self.assertFalse(application._boolean({0, 1, 2}))


class TestLargeGraphGeo(unittest.TestCase):
    """
    Tests against a large landscape
    """
    graph_file = "tests/data/test_landscape.json"
    subgraph_file = "tests/data/test_subgraph.json"

    def setUp(self):
        self.graph = self._hydrate(self.graph_file)
        self.subgraph = self._hydrate(self.subgraph_file)

        self.app = application.APP.test_client()

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_graph_success(self, mck_lm):
        """
        Test grabbing a full graph with geo coordinates
        """
        stack = 'stack-1'
        nova_2 = 'nova-2'
        server = 'machine-B'
        other = 'e5a7ec3e-7b25-478c-a1f1-8dc472444a3a'

        nodes = {}
        nodes[stack] = {"type": "LineString", "coordinates": [[0, 0], [2, 3]]}
        nodes[nova_2] = {"type": "Point", "coordinates": [21, 3]}
        nodes[other] = {"type": "Point", "coordinates": [21, 4]}
        nodes[server] = {"type": "Polygon", "coordinates": [[[0, 0], [10, 10],
                                                             [10, 0], [0, 0]]]}
        for node_id, geometry in nodes.iteritems():
            self.graph.node[node_id]['attributes']['geo'] = geometry

        # mock graph return
        json_gr = json.dumps(json_graph.node_link_data(self.graph))
        mck_lm.graph_db.get_graph.return_value = json_gr

        # Make REST call
        response = self.app.get("/graph?geo=True")
        feat_collection = json.loads(response.get_data())

        # Assertions
        self.assertEqual(self._geo(feat_collection, stack), nodes[stack])
        self.assertEqual(self._geo(feat_collection, nova_2), nodes[nova_2])
        self.assertEqual(self._geo(feat_collection, server), nodes[server])
        self.assertEqual(self._geo(feat_collection, other), nodes[other])
        self.assertEqual(len(feat_collection['features']), 4)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_graph_no_geo(self, mck_lm):
        """
        Test for no geo nodes in the graph
        """
        json_gr = json.dumps(json_graph.node_link_data(self.graph))
        mck_lm.graph_db.get_graph.return_value = json_gr

        # Make REST call
        response = self.app.get("/graph?geo=true")

        feature_collection = json.loads(response.get_data())
        self.assertEqual(feature_collection["features"], [])

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_subgraph_success(self, mck_lm):
        """
        Test grabbing a subgraph with geo coordinates
        """
        instance = '1ffaedbf-719a-4327-a14e-ed7b8564fb4e'
        server = 'machine-I'

        nodes = {}
        nodes[server] = {"type": "LineString", "coordinates": [[4, 5], [2, 3]]}
        nodes[instance] = {"type": "Point", "coordinates": [21, 3]}

        for node_id, geometry in nodes.iteritems():
            self.subgraph.node[node_id]['geo'] = geometry

        # mock graph return
        json_sgr = json.dumps(json_graph.node_link_data(self.subgraph))
        mck_lm.graph_db.get_subgraph.return_value = json_sgr

        # Make REST call
        response = self.app.get("/subgraph/lola?geo=True")
        feat_collection = json.loads(response.get_data())

        # Assertions
        self.assertEqual(self._geo(feat_collection, instance), nodes[instance])
        self.assertEqual(self._geo(feat_collection, server), nodes[server])
        self.assertEqual(len(feat_collection['features']), 2)

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_get_subgraph_no_geo(self, mck_lm):
        """
        Test for no geo nodes in the graph
        """
        json_sgr = json.dumps(json_graph.node_link_data(self.subgraph))
        mck_lm.graph_db.get_graph.return_value = json_sgr

        # Make REST call
        response = self.app.get("/graph?geo=1")

        feature_collection = json.loads(response.get_data())
        self.assertEqual(feature_collection["features"], [])

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_geo_false_graph(self, mck_lm):
        """
        Test that geo can be set to false
        """
        mck_lm.graph_db.get_graph.return_value = "Big graph"
        response = self.app.get("/graph?geo=false")

        self.assertEqual(response.get_data(), "Big graph")

    @mock.patch("landscaper.web.application.LANDSCAPE")
    def test_geo_false_subgraph(self, mck_lm):
        """
        Test that geo can be set to false
        """
        mck_lm.graph_db.get_subgraph.return_value = "subgraph"
        response = self.app.get("/subgraph/lola?geo=false")

        self.assertEqual(response.get_data(), "subgraph")

    @staticmethod
    def _geo(feature_collection, node_id):
        """
        Grab the geomtry objects from the feature collection for the matching
        node id.:
        :return: geometry object
        """
        for feature in feature_collection['features']:
            if feature['properties']['name'] == node_id:
                return feature['geometry']
        return None

    @staticmethod
    def _hydrate(filename):
        """
        Returns a networkx graph object.
        """
        graph_data = json.load(open(filename))
        return json_graph.node_link_graph(graph_data, directed=True)
