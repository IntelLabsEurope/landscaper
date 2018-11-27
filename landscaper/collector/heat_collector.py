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
Openstack heat collector class.
"""
import time

from landscaper.collector import base
from landscaper.common import LOG
from landscaper.utilities import openstack

# Node Structure.
IDEN_ATTR = {'layer': 'service', 'type': 'stack', 'category': 'compute'}
STATE_ATTR = {'stack_name': None, 'template': None}

# Events to listen for.
ADD_EVENTS = ['orchestration.stack.create.end']
DELETE_EVENTS = ['orchestration.stack.delete.end']
UPDATE_EVENTS = ['orchestration.stack.update.end',
                 'orchestration.stack.resume.end',
                 'orchestration.stack.suspend.end']


class HeatCollectorV1(base.Collector):
    """
    Collects stacks running in heat and links them to instances in the graph
    database.
    """
    def __init__(self, graph_db, conf_manager, event_manager):
        events = ADD_EVENTS + UPDATE_EVENTS + DELETE_EVENTS
        super(HeatCollectorV1, self).__init__(graph_db, conf_manager,
                                              event_manager, events)
        self.graph_db = graph_db
        self.heat = openstack.OpenStackClientRegistry().get_heat_v1_client()

    def init_graph_db(self):
        """
        Adds stack nodes to the graph database and connects them to the
        stack's vms.
        """

        LOG.info("[HEAT] Adding Heat components to the landscape.")
        now_ts = time.time()
        for stack in self.heat.stacks.list():
            if stack.stack_status == 'CREATE_COMPLETE':
                self._add_stack(stack, now_ts)

    def update_graph_db(self, event, body):
        """
        Updates the heat elements in the graph database.
        :param event: The event that has occurred.
        :param body: The details of the event that occurred.
        """
        from heatclient.exc import NotFound
        LOG.info("[HEAT] Processing event received: %s", event)
        now_ts = time.time()
        uuid = body.get('payload', dict()).get('stack_identity', 'UNDEFINED')
        if '/' in uuid:
            uuid = uuid.rsplit('/', 1)[1]
        try:
            stack = self.heat.stacks.get(uuid)
            if event in ADD_EVENTS:
                LOG.info("HEAT: Adding stack: %s", stack)
                self._add_stack(stack, now_ts)
            elif event in UPDATE_EVENTS:
                LOG.info("HEAT: Updating stack: %s", stack)
                self._update_stack(stack, now_ts)
            elif event in DELETE_EVENTS:
                LOG.info("HEAT: deleting stack: %s", stack)
                self._delete_stack(uuid, now_ts)
        except NotFound:
            LOG.warn("HEAT: Stack with UUID %s not found", uuid)

    def _delete_stack(self, uuid, timestamp):
        """
        Deletes the heat stack nodes from the database.
        :param uuid: Stack ID.
        :param timestamp: Time of deletion.
        """
        stack_node = self.graph_db.get_node_by_uuid(uuid)
        if stack_node:
            self.graph_db.delete_node(stack_node, timestamp)

    def _add_stack(self, stack, timestamp):
        """
        Adds a heat stack node to the graph database.
        :param stack: Heat stack object.
        :param timestamp: timestamp.
        """
        identity, state = self._create_heat_stack_nodes(stack)
        uuid = stack.id
        stack_node = self.graph_db.add_node(uuid, identity, state, timestamp)
        if stack_node is not None:
            resources = self._get_resources(uuid)
            for res in resources:
                self.graph_db.add_edge(stack_node, res, timestamp, "RUNS_ON")

    def _update_stack(self, stack, timestmp):
        """
        Manages an update to the heat stack.
        :param stack: Heat stack object.
        :param timestmp: timestamp.
        """
        _, state = self._create_heat_stack_nodes(stack)
        uuid = stack.id
        stack_node, _ = self.graph_db.update_node(uuid, state, timestmp)
        if stack_node is not None:
            resources = self._get_resources(uuid)
            for resource in resources:
                self.graph_db.update_edge(stack_node, resource,
                                          timestmp, "RUNS_ON")

    def _create_heat_stack_nodes(self, stack):
        """
        Creates the identity and state nodes for a heat stack.
        :param stack: Heat stack object.
        :return: Identity and state node.
        """
        identity = IDEN_ATTR.copy()
        state = STATE_ATTR.copy()
        uuid = stack.id
        state['stack_name'] = stack.stack_name
        template = self.heat.stacks.template(uuid)
        state['template'] = template
        return identity, state


    def _get_workload_output_params(self, workload_name):
        res = dict()
        params = dict()

        outputs = self.heat.stacks.get(workload_name).outputs
        for output in outputs:
            output_key = str(output['output_key'])
            if output_key.startswith('vm_'):
                values = output['output_value']
                if isinstance(values, (list,)): 
                    params[output_key] = output['output_value'][0]
                else:
                    params[output_key] = output['output_value']
        if len(params.keys()) > 0:
            res = params
        return res


    def _get_resources(self, stack_id):
        """
        Finds the resources created in the heat template which are in the
        graph database.
        :param stack_id: Heat stack id.
        :return: Graph database nodes associated with the heat stack.
        """
        nodes = list()
        resources = self.heat.resources.list(stack_id)
        for resource in resources:
            if resource.resource_type == 'OS::Heat::ResourceGroup':
                LOG.info('group -----------------------')
                params  = self._get_workload_output_params(stack_id)
                counter = 1

                LOG.info("PARAMS: {}".format(params))

                for k, v in params.iteritems():
                    LOG.info('{}: k={}, v={}'.format(counter, k, v))
                    counter += 1

                    res_node = self.graph_db.get_node_by_uuid(v)
                    if res_node is not None:
                        nodes.append(res_node)
            else:
                res_uuid = resource.physical_resource_id
                res_node = self.graph_db.get_node_by_uuid(res_uuid)
                if res_node is not None:
                    nodes.append(res_node)
        return nodes

