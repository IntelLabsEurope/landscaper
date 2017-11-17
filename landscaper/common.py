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
Global Variables used throughout the Landscaper.
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from landscaper import paths

# Setup Logger.
SERVICE_NAME = 'landscaper'
LOG = logging.getLogger(SERVICE_NAME)

# Create File Logger.
LOG_DIR = "{}/logs".format(paths.PROJECT_ROOT)
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
LOGF = "{}/landscaper.log".format(LOG_DIR)
RFILE_HANDLER = RotatingFileHandler(LOGF, maxBytes=1000000, backupCount=5)

# Create stderr Logger.
STDERR_HANDLER = logging.StreamHandler(sys.stderr)

# Set formatting.
FRMT_STR = '[%(asctime)s] [%(levelname)s] : %(message)s '
FORMATTER = logging.Formatter(FRMT_STR, "%Y-%m-%d %H:%M:%S %Z")
STDERR_HANDLER.setFormatter(FORMATTER)
RFILE_HANDLER.setFormatter(FORMATTER)

# Add the logger to the application.
LOG.addHandler(STDERR_HANDLER)
LOG.addHandler(RFILE_HANDLER)
LOG.setLevel(logging.INFO)


EOT_VALUE = 1924905600.0

NAME_PROP = "name"
LAYER_PROP = "layer"
CATEGORY_PROP = "category"
TYPE_PROP = "type"

IDEN_PROPS = [NAME_PROP,
              LAYER_PROP,
              CATEGORY_PROP,
              TYPE_PROP]

COLLECTOR_PACKAGE = 'landscaper.collector'
EVENT_LISTENER_PACKAGE = 'landscaper.event_listener'
GRAPH_PACKAGE = 'landscaper.graph_db'
