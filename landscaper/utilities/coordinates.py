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
Retrieval of coordinates.
"""
import json

from landscaper import paths


class Geo(object):
    """
    Extracts feature collection
    """
    @staticmethod
    def extract_geo(json_str):
        """
        Build feature collection object from a networkx json graph.
        :param json_str: networkx json graph
        :return: GeoJSON feature collection
        """
        json_dict = json.loads(json_str)
        features = []
        for node in json_dict['nodes']:
            # test for attributes first
            geo = {}
            if 'attributes' in node:
                if 'geo' in node['attributes']:
                    geo = node['attributes']['geo']
            else:
                if 'geo' in node:
                    geo = node['geo']

            if geo:
                name = node['name']
                feature = {"type": "Feature",
                           "geometry": geo,
                           "properties": {"name": name}}
                features.append(feature)

        feat_collection = {"type": "FeatureCollection", "features": features}

        return json.dumps(feat_collection)


def component_coordinates(component_name, component_type):
    """
    Returns the coordinates for a given component. The component is identified
    by the component name and component type. The coordinates are retrieved
    from a json file.
    :param component_name: Name/id of the component.
    :param component_type: Type of component.
    :return: Tuple containing the latitude and longitude in that order.
    """
    coordinates = load_coordinates()
    for component in coordinates.get(component_type, []):
        if component["name"] == component_name:
            return (component["latitude"], component["longitude"])
    return None


def load_coordinates():
    """
    Load the coordinates from the coordinates json file.
    :return: JSON containing all of the coordinates.
    """
    return json.load(open(paths.COORDINATES))
