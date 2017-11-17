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
Tests for coordinates retrieval
"""
import os
import json
import numbers
import unittest
import mock

from landscaper import paths
from landscaper.utilities import coordinates


class TestCoordinatesJson(unittest.TestCase):
    """
    Unit tests for the coordinates json file.
    """

    def test_get_coordinates_json_path(self):
        """
        Check that the path is availabe to the coordinates.
        """
        self.assertTrue(hasattr(paths, "COORDINATES"))

    def test_path_to_json_works(self):
        """
        Check that the coordinates file is where it is supposed to be.
        """
        self.assertTrue(os.path.isfile(paths.COORDINATES))

    def test_coordinates_json_good(self):
        """
        Check that the json is formatted correctly.
        """
        try:
            test_coordinates = json.load(open(paths.COORDINATES))
        except ValueError:
            self.fail("Couldn't parse coordinates json file. Malformed json")

        try:
            for _, physical_components in test_coordinates.iteritems():
                for component in physical_components:
                    self.assertIsInstance(component['name'], basestring)
                    self.assertIsInstance(component['latitude'], numbers.Real)
                    self.assertIsInstance(component['longitude'], numbers.Real)
        except KeyError:
            self.fail("Wrong structure for json file.")


class TestCoordinatesRetrieval(unittest.TestCase):
    """
    Unit tests to test the retrieve coordinates functionality.
    """

    def setUp(self):
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        self.coords_path = os.path.join(tests_dir, 'data/coordinates.json')

    def test_unknown_type(self):
        """
        Check that an incorrect type is ignored even when the id is there in
        another list.
        """
        coords = coordinates.component_coordinates("machine-A", "hammer")
        self.assertIsNone(coords)

    def test_unknown_name(self):
        """
        Type is available, but name is not.
        """
        coords = coordinates.component_coordinates("machine-K", "machine")
        self.assertIsNone(coords)

    @mock.patch("landscaper.utilities.coordinates.paths")
    def test_grab_machine_coordinates(self, mck_paths):
        """
        Retrieve machine coordinates.
        """
        mck_paths.COORDINATES = self.coords_path

        coords_b = coordinates.component_coordinates("machine-B", "machine")
        coords_c = coordinates.component_coordinates("machine-C", "machine")
        self.assertEqual(coords_b, (40.45712, -78.254))
        self.assertEqual(coords_c, (53.374641, -6.522470))

    @mock.patch("landscaper.utilities.coordinates.paths")
    def test_grab_switch_coordinates(self, mck_paths):
        """
        Retrieve switch coordinates.
        """
        mck_paths.COORDINATES = self.coords_path
        coordinates_v = coordinates.component_coordinates("switch-V", "switch")
        coordinates_k = coordinates.component_coordinates("switch-K", "switch")
        self.assertEqual(coordinates_v, (-3.2, -40))
        self.assertEqual(coordinates_k, (-20.78, 130.5644))
