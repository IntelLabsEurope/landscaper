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


class TestCoordinatesRetrieval(unittest.TestCase):
    """
    Unit tests to test the retrieve coordinates functionality.
    """

    def setUp(self):
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        self.coords_path = os.path.join(tests_dir, 'data/coordinates.json')

    @mock.patch("landscaper.utilities.coordinates.paths")
    def test_unknown_name(self, mck_paths):
        """
        Check that a name that does not exist is ignored.
        """
        mck_paths.COORDINATES = self.coords_path
        coords = coordinates.component_coordinates("machine-G")
        self.assertIsNone(coords)

    @mock.patch("landscaper.utilities.coordinates.paths")
    def test_none_name(self, mck_paths):
        """
        Check that a None value input is ignored.
        """
        mck_paths.COORDINATES = self.coords_path
        coords = coordinates.component_coordinates(None)
        self.assertIsNone(coords)

    @mock.patch("landscaper.utilities.coordinates.paths")
    def test_grab_machine_coordinates(self, mck_paths):
        """
        Retrieve machine coordinates for Point, LineString and Polygon format.
        """
        mck_paths.COORDINATES = self.coords_path

        coords_b = coordinates.component_coordinates("machine-B")
        coords_c = coordinates.component_coordinates("machine-C")
        coords_d = coordinates.component_coordinates("machine-D")
        self.assertEqual(coords_b, {
            "type": "Point",
            "coordinates": [-78.254, 40.45712]
            })
        self.assertEqual(coords_c, {
            "type": "LineString",
            "coordinates": [
                [102.0, 0.0], [103.0, 1.0], [104.0, 0.0], [105.0, 1.0]
                ]
        })
        self.assertEqual(coords_d, {
            "type": "Polygon",
            "coordinates": [
                [[100.0, 0.0], [101.0, 0.0], [101.0, 1.0],
                 [100.0, 1.0], [100.0, 0.0]]
                ]
        })
