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
REST Application for the landscape.
"""
import ast
import time

import flask
from flask import request
from flask import Response
from flask import abort

from landscaper.common import LOG
from landscaper import landscape_manager as lm

APP = flask.Flask(__name__)
LANDSCAPE = None
MIME = "application/json"


@APP.route("/graph")
def get_graph():
    """
    Returns the full landscape graph as node-link json.
    """
    LOG.info("Retrieving Landscape with url : %s", request.url)
    return Response(LANDSCAPE.graph_db.get_graph(), mimetype=MIME)


@APP.route("/subgraph/<node_id>")
def get_subgraph(node_id):
    """
    Returns the subgraph using a node id as the start.
    """
    LOG.info("Retrieving Subgraph with url %s", request.url)
    timestamp = request.args.get("timestamp")
    time_frame = request.args.get("timeframe", 0)
    subgraph = LANDSCAPE.graph_db.get_subgraph(node_id, timestmp=timestamp,
                                               timeframe=time_frame)
    if not subgraph:
        err_msg = "Node with ID '{}', not in the landscape.".format(node_id)
        LOG.error(err_msg)
        abort(400, err_msg)

    return Response(subgraph, mimetype=MIME)


@APP.route("/node/<node_id>")
def get_node_by_uuid(node_id):
    """
    Returns a networkx graph containing the node.
    """
    LOG.info("Retrieving node by uuid, with url %s", request.url)
    graph = LANDSCAPE.graph_db.get_node_by_uuid_web(node_id)

    if not graph:
        err_msg = "Node with ID '{}', not in the landscape.".format(node_id)
        LOG.error(err_msg)
        abort(400, err_msg)

    return Response(graph, mimetype=MIME)


@APP.route("/nodes")
def get_node_by_properties():
    """
    Returns a graph containing just the nodes that match the properties.
    """
    LOG.info("Retrieving node by props with url %s", request.url)
    timestamp = request.args.get("timestamp") or time.time()
    time_frame = request.args.get("timeframe", 0)
    properies_string = request.args.get("properties")
    if not properies_string:
        err_msg = "Properties must be specified."
        LOG.warn(err_msg)
        abort(400, err_msg)
    properties = ast.literal_eval(properies_string)
    graph = LANDSCAPE.graph_db.get_node_by_properties_web(properties,
                                                          timestamp,
                                                          time_frame)
    return Response(graph, mimetype=MIME)


@APP.before_first_request
def initilise_application():
    """
    Setup the application before it is run.
    """
    global LANDSCAPE
    if not LANDSCAPE:
        LANDSCAPE = lm.LandscapeManager()
