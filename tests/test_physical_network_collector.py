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
Tests for the physical network collector.
"""
import os
import unittest
import logging
import mock
import yaml

from landscaper import paths
from landscaper.collector import physical_network_collector as pnc

# W0212 -  Access to a protected member
# pylint: disable=W0212


class TestGeneralPhysicalNetworkCollector(unittest.TestCase):
    """
    General tests for the physical network collector.
    """
    def test_path_to_switch_description(self):
        """
        Test that there is a path to the switch description file in paths.
        """
        self.assertIsNotNone(paths.NETWORK_DESCRIPTION)

    def test_network_description_file(self):
        """
        Test that the file exists.
        """
        network_description = open(paths.NETWORK_DESCRIPTION)
        self.assertIsNotNone(network_description)


class TestGetSwitchInfo(unittest.TestCase):
    """
    Unittests for the '_get_switch_info' method.
    """
    def setUp(self):
        self.net_desc_path = _test_network_description_path()
        self.collector = pnc.PhysicalNetworkCollector(None, None, None)

    def test_get_switch_info(self):
        """
        Check that get info is parsing the description file correctly.
        """
        switch_info = self.collector._network_description(self.net_desc_path)
        expctd = {'switch_two': {'bandwidth': '1Gb',
                                 'role': ['management', 'exterior'],
                                 'name': 'Second switch',
                                 'connected-devices': ['A7-C2-09-70-78-B3']},
                  'switch_one': {'bandwidth': '40Gb',
                                 'role': ['storage', 'data'],
                                 'name': 'First switch',
                                 'connected-devices': ['33-FE-E1-0E-B3-2E',
                                                       'C2-5D-77-B5-E9-63']}}
        self.assertDictEqual(switch_info, expctd)


class TestCreateSwitchNodes(unittest.TestCase):
    """
    Unittests for the '_create_switch_nodes' method.
    """
    def setUp(self):
        self.net_desc_path = _test_network_description_path()
        self.collector = pnc.PhysicalNetworkCollector(None, None, None)

    def test_identity_node_matches(self):
        """
        Tests that the identity node matches the global node layout
        """
        idenity_node, _ = self.collector._create_switch_nodes({})
        self.assertDictEqual(idenity_node, pnc.IDENTITY)

    def test_identity_node_keys(self):
        """
        Test that we have the correct keys in the identity node.
        """
        identity_node, _ = self.collector._create_switch_nodes({})
        self.assertItemsEqual(identity_node.keys(), ['type', 'category',
                                                     'layer'])

    def test_state_node_keys_match(self):
        """
        Test that the keys match the global STATE. We do this to ensure that
        there are no added attributes to the state node, or that none are
        removed.
        """
        _, state_node = self.collector._create_switch_nodes({})
        self.assertItemsEqual(state_node.keys(), pnc.STATE)

    def test_values_packed_into_state(self):
        """
        Ensure that all of the values are packed into the state correctly.
        """
        switch_info = {'name': 'switch_three', 'roles': ['exterior'],
                       'bandwidth': '1Gb', 'random': 'attribute',
                       'connected-devices': ['dev1', 'dev2']}
        _, state = self.collector._create_switch_nodes(switch_info)
        expected_state = {'switch_name': 'switch_three', 'roles': ['exterior'],
                          'bandwidth': '1Gb'}
        self.assertDictEqual(state, expected_state)


class TestAddSwitch(unittest.TestCase):
    """
    Unittests for the '_add_switch' method
    """
    collector_module = "landscaper.collector.physical_network_collector"

    def setUp(self):
        self.net_desc = _test_network_description()
        self.mck_graph_db = mock.Mock()
        self.collector = pnc.PhysicalNetworkCollector(self.mck_graph_db, None,
                                                      None)

    @mock.patch(collector_module + ".PhysicalNetworkCollector._nic_node")
    def test_switch_added_to_database(self, nic_node_mock):
        """
        Test that the add_switch method is called.
        """
        switch_id = 'switch_four'
        switch_info = {'name': 'fourth_switch', 'roles': ['exterior'],
                       'bandwidth': '1Gb', 'random': 'attribute',
                       'connected-devices': ['dev1', 'dev2']}
        timestamp = 5
        nic_node_mock.return_value = []
        self.collector._add_switch(switch_id, switch_info, 5)

        identity, state = self.collector._create_switch_nodes(switch_info)
        self.mck_graph_db.add_node.assert_called_once_with(switch_id, identity,
                                                           state, timestamp)

    @mock.patch(collector_module + ".PhysicalNetworkCollector._nic_node")
    def test_grabbing_nodes_to_connect(self, nic_node_mock):
        """
        Check that the nics are being grabbed from the graph database so that
        they can be connected to the switches.
        """
        # add a switch
        switch_id = 'switch_one'
        switch = self.net_desc[switch_id]
        timestamp = 9.0
        self.collector._add_switch(switch_id, switch, timestamp)

        # check that the database is queried for appropriate nics.
        prop_calls = nic_node_mock.call_args_list
        for mac in switch['connected-devices']:
            self.assertIn(mock.call(mac), prop_calls)

    @mock.patch(collector_module + ".PhysicalNetworkCollector._nic_node")
    def test_connecting_nodes(self, nic_node_mock):
        """
        Check that the nics are being connected to the switch.
        """
        switch_node = 'switch_five'
        nic_nodes = ['nic_1', 'nic_2']
        timestamp = 43
        switch_info = {'connected-devices': [1, 2]}

        # Setting up db return values
        self.mck_graph_db.add_node.return_value = switch_node
        nic_node_mock.side_effect = nic_nodes
        self.collector._add_switch(None, switch_info, timestamp)

        edge_calls = self.mck_graph_db.add_edge.call_args_list
        for nic in nic_nodes:
            edge_call = mock.call(nic, switch_node, timestamp, "COMMUNICATES")
            self.assertIn(edge_call, edge_calls)

    @mock.patch(collector_module + ".PhysicalNetworkCollector._nic_node")
    @mock.patch("landscaper.collector.physical_network_collector.LOG")
    def test_no_nic_node(self, mck_log, nic_node_mock):
        """
        ensure the collector can handle a mac that does not match a nic in the
        database.
        """
        switch_node = 'switch_six'

        # Setting up db return values
        self.mck_graph_db.add_node.return_value = switch_node
        nic_node_mock.return_value = None
        self.collector._add_switch(switch_node, {'connected-devices': [1]}, 2)

        # No edge is added
        self.mck_graph_db.add_edge.assert_not_called()

        # And we log the warning
        self.assertEqual(mck_log.warning.call_count, 1)


class TestNicNode(unittest.TestCase):
    """
    Unittests for the '_nic_node' method
    """
    def setUp(self):
        self.mck_graph_db = mock.Mock()
        self.collector = pnc.PhysicalNetworkCollector(self.mck_graph_db, None,
                                                      None)

    def test_for_success(self):
        """
        Assuming that the nic node is in the database. Ensure it is returned
        correctly.
        """
        fake_node = "fake_switch_node"
        fake_nic = "fake_nic"
        mac = "9a:6a:24:36:ab:b9"
        param = {"address": mac}
        self.mck_graph_db.get_nodes_by_properties.return_value = [fake_node]
        self.mck_graph_db.predecessors.return_value = [(fake_nic, "edge")]
        nic_node = self.collector._the_node(mac)

        self.mck_graph_db.get_nodes_by_properties.assert_called_with(param)
        self.mck_graph_db.predecessors.assert_called_with(fake_node)
        self.assertEqual(nic_node, fake_nic)

    def test_mac_not_found(self):
        """
        Check that the mac address cannot be found in the database.
        """
        self.mck_graph_db.get_nodes_by_properties.return_value = None
        nic_node = self.collector._the_node("0F:61:BF:6F:63:0D")
        self.assertIsNone(nic_node)

    def test_no_predecessors(self):
        """
        When no predecessors then return none.
        """
        fake_node = "cardboard_node"
        self.mck_graph_db.get_nodes_by_properties.return_value = [fake_node]
        self.mck_graph_db.predecessors.return_value = []
        nic_node = self.collector._the_node("BA:FA:6A:F0:79:66")

        self.assertIsNone(nic_node)


class TestInitGraphDB(unittest.TestCase):
    """
    Unittests for the 'init_graph_db' method
    """
    collector_module = "landscaper.collector.physical_network_collector"

    def setUp(self):
        self.mck_graph_db = mock.Mock()
        self.collector = pnc.PhysicalNetworkCollector(self.mck_graph_db, None,
                                                      None)

    @mock.patch(collector_module + ".paths")
    @mock.patch(collector_module + ".PhysicalNetworkCollector._add_switch")
    @mock.patch(collector_module + ".time")
    def test_add_switches_adds_switches(self, mck_time, add_switch, mck_paths):
        """
        Ensure switches are being added.
        """
        timestamp = 34
        mck_paths.NETWORK_DESCRIPTION = _test_network_description_path()
        mck_time.time.return_value = timestamp
        self.collector.init_graph_db()

        net_desc = _test_network_description()

        add_switch_calls = add_switch.call_args_list
        for switch, switch_info in net_desc.iteritems():
            add_switch_call = mock.call(switch, switch_info, timestamp)
            self.assertIn(add_switch_call, add_switch_calls)


def _test_network_description():
    """
    returns the test net description dictionary.
    """
    path = _test_network_description_path()
    return yaml.load(open(path))


def _test_network_description_path():
    """
    Gets the path to the test network description file.
    """
    return os.path.join(os.getcwd(), "tests/data/test_net_description.yaml")


def setUpModule():
    """
    Disable logging before tests.
    """
    logging.disable(logging.CRITICAL)


def tearDownModule():
    """
    reenable logging after the tests.
    """
    logging.disable(logging.NOTSET)