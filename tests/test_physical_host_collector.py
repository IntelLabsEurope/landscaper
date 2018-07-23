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
Tests for the physical host collector.
"""
import logging
import unittest
import os
import xml.etree.ElementTree as Et
import mock

from networkx import DiGraph

from landscaper.collector import physical_host_collector as phc

# W0212 -  Access to a protected member
# pylint: disable=W0212


class TestCoordinates(unittest.TestCase):
    """
    Tests which ensure that the coordinates are being collected and built
    correctly and that they are attaching to the node before it goes to the db.
    """

    hwloc_class = "landscaper.collector.physical_host_collector.HWLocCollector"

    def setUp(self):
        self.graph = DiGraph()
        self.graph.add_node("machine-A", {"type": "machine",
                                          "attributes": {"os": "linux",
                                                         "nics": "2",
                                                         "serial": "5"}})
        self.graph.add_node("machine-C", {"type": "machine",
                                          "attributes": {"cooling": "fan",
                                                         "serial": "6"}})
        self.graph.add_node("switch-V", {"type": "switch",
                                         "attributes": {"bandwidth": "40",
                                                        "ports": "48"}})
        self.collector = phc.HWLocCollector(None, mock.Mock(), mock.Mock())
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)

    def test_add_coordinates_to_node(self):
        """
        Test that add coordinates method adds the coordinates to the node.
        """
        node = "machine-A"
        self.assertNotIn("coordinates", self.graph.node[node]["attributes"])
        self.collector._add_coordinates(self.graph, node)
        self.assertIn("coordinates", self.graph.node[node]["attributes"])

    @mock.patch("landscaper.collector.physical_host_collector.coordinates")
    def test_correct_coordinates_added(self, mck_coordinates):
        """
        Test that the correct coordinates are retrieved.
        """
        mck_coordinates.component_coordinates.return_value = "geo_data"
        node_s = "switch-V"
        self.collector._add_coordinates(self.graph, node_s)
        coordinates_s = self.graph.node[node_s]["attributes"]["coordinates"]
        self.assertEqual(coordinates_s, "geo_data")
        mck_coordinates.component_coordinates.assert_called_with(node_s)

        node_m = "machine-C"
        self.collector._add_coordinates(self.graph, node_m)
        coordinates_m = self.graph.node[node_m]["attributes"]["coordinates"]
        self.assertEqual(coordinates_m, "geo_data")
        mck_coordinates.component_coordinates.assert_called_with(node_m)
        coords_called = mck_coordinates.component_coordinates.call_count
        self.assertEqual(coords_called, 2)

    @mock.patch(hwloc_class + "._get_hwloc")
    @mock.patch(hwloc_class + "._get_cpu_info")
    def test_coordinates_add(self, mck_cpuinfo, mck_get_loc):
        """
        Ensures that the coordinates are sent to the database.
        """
        # Fake hwloc file used
        machine = "machine-A"
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        hwloc_file = "{}_hwloc.xml".format(machine)
        hwloc_path = os.path.join(tests_dir, 'data', hwloc_file)
        mck_get_loc.return_value = Et.parse(hwloc_path).getroot()

        # Remove cpu_info
        mck_cpuinfo.return_value = None

        # Add physical machine to the database
        graphdb_mock = mock.Mock()
        confmgr_mock = mock.Mock()
        eventmgr_mock = mock.Mock()
        confmgr_mock.get_types_to_filter.return_value = []
        collector = phc.HWLocCollector(graphdb_mock, confmgr_mock, eventmgr_mock)
        collector._add_physical_machine("machine-A", 12)

        # Find the machine node call + check that coordinates have been added.
        for call in graphdb_mock.add_node.call_args_list:
            node_name = call[0][0]
            if node_name == machine:
                attributes = call[0][2]
                self.assertIn('coordinates', attributes)
                break

    def test__remove_physical_machine(self):
        """
        Ensures that the coordinates are removed from the database.
        """
        # Fake hwloc file used
        machine = "machine-A"
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        hwloc_file = "{}_hwloc.xml".format(machine)
        hwloc_path = os.path.join(tests_dir, 'data', hwloc_file)
        # Remove physical machine from the database
        graphdb_mock = mock.Mock()
        graphdb_mock.get_node_by_uuid.return_value = machine
        confmgr_mock = mock.Mock()
        eventmgr_mock = mock.Mock()
        collector = phc.HWLocCollector(graphdb_mock, confmgr_mock, eventmgr_mock)
        collector._remove_physical_machine("machine-A", 12)

        # Find the machine node call + check that coordinates have been deleted.
        exists = False
        for call in graphdb_mock.delete_node.call_args_list:
            node_name = call[0][0]
            if node_name == machine:
                exists = True
                break
        self.assertIs(exists, True)