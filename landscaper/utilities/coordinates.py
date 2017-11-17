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
