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
Keeps track of all of the paths in the landscaper.
"""
import os
PROJECT_ROOT = os.path.split(os.path.dirname(os.path.abspath(__file__)))[0]
CONF_FILE = os.path.join(PROJECT_ROOT, "landscaper.cfg")
#IMPORTANT: Ensure DATA_DIR path does not conflict with :
#   1. Paths in volumes section in docker-compose.yaml file
#   2. hwloc_folder / cpuinfo_folder values in landscaper.cfg file
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

LANDSCAPER_MOD = os.path.join(PROJECT_ROOT, "landscaper")
EVENT_LISTENER_DIR = os.path.join(LANDSCAPER_MOD, "event_listener")
COLLECTOR_DIR = os.path.join(LANDSCAPER_MOD, "collector")
GRAPH_DB_DIR = os.path.join(LANDSCAPER_MOD, "graph_db")
COORDINATES = os.path.join(DATA_DIR, "coordinates.json")
NETWORK_DESCRIPTION = os.path.join(DATA_DIR, "network_description.yaml")
