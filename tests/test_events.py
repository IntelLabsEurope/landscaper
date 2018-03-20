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
Tests event update methods for core openstack collectors.
"""
import cPickle as pickle
import logging
import unittest
import mock
from mock import patch

from landscaper import events_manager
from landscaper.collector import heat_collector
from landscaper.collector import nova_collector
from landscaper.collector import neutron_collector
from landscaper.collector import cinder_collector
from landscaper.utilities import configuration
from landscaper.graph_db import neo4j_db
from landscaper.event_listener import os_rabbitmq_listener

from tests.test_utils import utils

# pylint: disable=W0212
LOG = logging.getLogger(__name__)


class TestOpenstackCollectorEvents(unittest.TestCase):
    """
    Test the events for the openstack collectors.
    """
    nova_module = "landscaper.collector.nova_collector"

    def setUp(self):
        utils.create_test_config()
        test_conf = utils.TEST_CONFIG_FILE
        self.conf_manager = configuration.ConfigurationManager(test_conf)
        self.events_manager = events_manager.EventsManager()
        self.graph_db = neo4j_db.Neo4jGDB(self.conf_manager)

        # Disable logging.
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        utils.remove_test_config()
        self.graph_db.delete_all()
        logging.disable(logging.NOTSET)

    @patch("landscaper.collector.heat_collector.openstack")
    @patch("landscaper.collector.heat_collector.time")
    def _add_stack(self, stack_id, stack_name, resource_ids, mck_time, mck_os):
        mck_time.time.return_value = "1502828001"
        stack_obj = self._to_object({"id": stack_id, "stack_name": stack_name})
        heat = mck_os.OpenStackClientRegistry().get_heat_v1_client()
        heat.stacks.get.return_value = stack_obj
        heat.stacks.template.return_value = "<>"

        resources = []
        for res_id in resource_ids:
            resources.append(self._to_object({"physical_resource_id": res_id}))
        heat.resources.list.return_value = resources

        heat_coll = heat_collector.HeatCollectorV1(self.graph_db,
                                                   self.conf_manager,
                                                   self.events_manager)

        event_body = {"payload": {"stack_identity": stack_id}}
        heat_coll.update_graph_db(heat_collector.ADD_EVENTS[0], event_body)

    @patch("landscaper.collector.nova_collector.openstack")
    @patch("landscaper.collector.nova_collector.time")
    def _delete_nova_instance(self, instance_id, mck_time, _):
        mck_time.time.return_value = "1502825001"
        event_body = {"payload": {"instance_id": instance_id}}
        delete_event = nova_collector.DELETE_EVENTS[0]
        nova_coll = nova_collector.NovaCollectorV2(self.graph_db,
                                                   self.conf_manager,
                                                   self.events_manager)
        nova_coll.update_graph_db(delete_event, event_body)

    @patch("landscaper.collector.neutron_collector.openstack")
    @patch("landscaper.collector.neutron_collector.time")
    def _delete_neutron_vnic(self, port_id, mck_time, _):
        mck_time.time.return_value = "1502825001"
        delete_port_event = neutron_collector.PORT_DELETE_EVENTS[0]
        event_body = {"payload": {"port_id": port_id}}
        neutron_col = neutron_collector.NeutronCollectorV2(self.graph_db,
                                                           self.conf_manager,
                                                           self.events_manager)
        neutron_col.update_graph_db(delete_port_event, event_body)

    @patch("landscaper.collector.cinder_collector.openstack")
    @patch("landscaper.collector.cinder_collector.time")
    def _delete_cinder_volume(self, volume_id, mck_time, _):
        mck_time.time.return_value = "1502825001"
        delete_volume_event = cinder_collector.DELETE_EVENTS[0]
        event_body = {"payload": {"volume_id": volume_id}}
        cinder_coll = cinder_collector.CinderCollectorV2(self.graph_db,
                                                         self.conf_manager,
                                                         self.events_manager)
        cinder_coll.update_graph_db(delete_volume_event, event_body)

    @patch("landscaper.collector.heat_collector.openstack")
    @patch("landscaper.collector.heat_collector.time")
    def _delete_heat_stack(self, stack_id, mck_time, _):
        mck_time.time.return_value = "1502825001"
        delete_stack_event = heat_collector.DELETE_EVENTS[0]
        event_body = {"payload": {'stack_identity': stack_id}}
        heat_coll = heat_collector.HeatCollectorV1(self.graph_db,
                                                   self.conf_manager,
                                                   self.events_manager)
        heat_coll.update_graph_db(delete_stack_event, event_body)

    @patch("landscaper.collector.nova_collector.openstack")
    @patch("landscaper.collector.nova_collector.time")
    def _add_nova_instance(self, uuid, host, name, mck_time, _):
        mck_time.time.return_value = "1502828001"
        nova_coll = nova_collector.NovaCollectorV2(self.graph_db,
                                                   self.conf_manager,
                                                   self.events_manager)
        add_event = nova_collector.ADD_EVENTS[0]
        event_body = {"payload": {"instance_id": uuid, "display_name": name,
                                  "host": host}}
        nova_coll.update_graph_db(add_event, event_body)

    @patch("landscaper.collector.neutron_collector.openstack")
    @patch("landscaper.collector.neutron_collector.time")
    def _add_neutron_port(self, prt_id, net_id, instance_id, mck_time, _):
        mck_time.time.return_value = "1502828001"
        neutron_col = neutron_collector.NeutronCollectorV2(self.graph_db,
                                                           self.conf_manager,
                                                           self.events_manager)
        add_event = neutron_collector.PORT_ADD_EVENTS[0]
        event_body = {"payload": {"port": {"id": prt_id,
                                           "network_id": net_id,
                                           "device_id": instance_id}}}
        neutron_col.update_graph_db(add_event, event_body)

    @staticmethod
    def _to_object(variables):
        return type("object", (object,), variables)

    @patch("landscaper.collector.cinder_collector.openstack")
    @patch("landscaper.collector.cinder_collector.time")
    def _add_volume(self, instance, volume_id, mck_time, _):
        mck_time.time.return_value = "1502828001"

        event_body = {"payload": {"volume_id": volume_id,
                                  "volume_attachment":
                                      [{"instance_uuid": instance,
                                        "attach_status": "attached"}]}}
        cinder_coll = cinder_collector.CinderCollectorV2(self.graph_db,
                                                         self.conf_manager,
                                                         self.events_manager)
        add_volume_event = cinder_collector.ADD_EVENTS[0]
        cinder_coll.update_graph_db(add_volume_event, event_body)

    def test_create_service(self):
        """
        Test that events are reflected in the landscape.
        """
        # Add Vms
        host = "machine-A"
        nova_instance_1 = "nova-1"
        nova_instance_2 = "nova-2"

        self._add_nova_instance(nova_instance_1, host, nova_instance_1)
        self._add_nova_instance(nova_instance_2, host, nova_instance_2)

        # Add Vnics
        network = "598fd41d-5118-48e5-9b75-862ad070a1e3"
        neutron_port_1 = "neutron-port-1"
        neutron_port_2 = "neutron-port-2"
        self._add_neutron_port(neutron_port_1, network, nova_instance_1)
        self._add_neutron_port(neutron_port_2, network, nova_instance_2)

        # Add Volume
        volume = "volume-2"
        self._add_volume(nova_instance_1, volume)

        # Add Stack
        stack = "stack-1"
        resources = [nova_instance_1, nova_instance_2, neutron_port_1,
                     neutron_port_2, volume]
        self._add_stack(stack, "yew", resources)

        landscape = self.graph_db.get_graph(json_out=False)

        self.assertIsNotNone(landscape[stack])
        self.assertIsNotNone(landscape[neutron_port_1])
        self.assertIsNotNone(landscape[volume])


class TestNeutronEvents(unittest.TestCase):
    """
    Integration tests for neutron events.
    """
    landscape_file = "tests/data/test_landscape_with_states.json"

    def setUp(self):
        conf_manager = configuration.ConfigurationManager()
        event_manager = events_manager.EventsManager()
        # Set up the graph database.
        self.graph_db = neo4j_db.Neo4jGDB(conf_manager)
        self.graph_db.delete_all()
        self.graph_db.load_test_landscape(self.landscape_file)

        # Patch up nova and neutron openstack.
        nova_patch = patch('landscaper.collector.nova_collector.openstack')
        net_patch = patch('landscaper.collector.neutron_collector.openstack')
        self.addCleanup(nova_patch.stop)
        self.addCleanup(net_patch.stop)
        nova_patch.start()
        net_patch.start()

        # Set up landscaper classes.
        self.listener = os_rabbitmq_listener.OSRabbitMQListener(event_manager,
                                                                conf_manager)
        nova_collector.NovaCollectorV2(self.graph_db, conf_manager,
                                       event_manager)
        neutron_collector.NeutronCollectorV2(self.graph_db, conf_manager,
                                             event_manager)
        logging.disable(logging.ERROR)

    def tearDown(self):
        self.graph_db.delete_all()
        logging.disable(logging.NOTSET)

    def test_vnic_attaches(self):
        """
        The vnic attaches to the network and the vm attaches to the vnic.
        """
        vnic = '26b65fc8-03be-41a6-9615-f1c123e0f78a'
        instance = '7593155e-da6b-4b62-9d25-8196b7138f80'
        network = '598fd41d-5118-48e5-9b75-862ad070a1e3'
        machine = 'machine-B'

        # Launch the events against the database.
        _simulate_events(self.listener, 'tests/data/events/add_1_stack.p')
        vm_subgraph = self.graph_db.get_subgraph(instance, json_out=False)

        # Check that the vm is connecting properly.
        vm_successors = vm_subgraph.successors(instance)
        self.assertEqual(len(vm_successors), 2)
        self.assertTrue(vnic in vm_successors)
        self.assertTrue(machine in vm_successors)

        # Check the vnic is attaching to the network.
        vnic_successors = vm_subgraph.successors(vnic)
        self.assertEqual(len(vnic_successors), 1)
        self.assertTrue(network in vnic_successors)


class TestCinderEvents(unittest.TestCase):
    """
    Integration tests for testing the cinder events.
    """
    landscape_file = "tests/data/test_landscape_with_states.json"

    def setUp(self):
        # Initialise managers with test config..
        utils.create_test_config()
        conf = configuration.ConfigurationManager(utils.TEST_CONFIG_FILE)
        event_m = events_manager.EventsManager()

        # Set up the graph database.
        self.graph_db = neo4j_db.Neo4jGDB(conf)
        self.graph_db.delete_all()
        self.graph_db.load_test_landscape(self.landscape_file)

        # Patch up nova and neutron openstack.
        nova_patch = patch('landscaper.collector.nova_collector.openstack')
        cinder_patch = patch(
            'landscaper.collector.cinder_collector.openstack')
        self.addCleanup(nova_patch.stop)
        self.addCleanup(cinder_patch.stop)
        nova_patch.start()
        cinder_patch.start()

        # Set up landscaper classes.
        self.listener = os_rabbitmq_listener.OSRabbitMQListener(event_m,
                                                                conf)
        nova_collector.NovaCollectorV2(self.graph_db, conf, event_m)
        cinder_collector.CinderCollectorV2(self.graph_db, conf, event_m)
        logging.disable(logging.ERROR)

    def tearDown(self):
        self.graph_db.delete_all()
        logging.disable(logging.NOTSET)

    def test_volume_attaches_to_vm(self):
        """
        Ensure that the volume is attached to the vm.
        """
        volume = 'd79a82fa-a195-4086-beee-5c449c981708'
        instance = '7593155e-da6b-4b62-9d25-8196b7138f80'

        _simulate_events(self.listener, 'tests/data/events/add_1_stack.p')
        vm_graph = self.graph_db.get_subgraph(instance, json_out=False)
        vm_successors = vm_graph.successors(instance)

        self.assertTrue(len(vm_successors), 2)
        self.assertTrue('machine-B' in vm_successors)
        self.assertTrue(volume in vm_successors)

    def test_volume_deleted(self):
        """
        Check that the volume is deleted.
        As the nova collector is instantiated vm deletions occur also.
        """
        volume = 'd79a82fa-a195-4086-beee-5c449c981708'
        instance = '7593155e-da6b-4b62-9d25-8196b7138f80'

        # Add the components
        _simulate_events(self.listener, 'tests/data/events/add_1_stack.p')
        before_delete = self.graph_db.get_graph(json_out=False)

        # Remove the components
        _simulate_events(self.listener, 'tests/data/events/delete_1_stack.p')
        after_delete = self.graph_db.get_graph(json_out=False)

        # Compare
        diff = utils.compare_graph(before_delete, after_delete)
        self.assertItemsEqual([volume, instance], diff['removed'])


def _simulate_events(listener, event_file):
    """
    Simulates the events in the pickled file. THe timing of events is also
    preserved. THe events are fired directly at the rabbit handler
    callback.
    :param listener: An event listener.
    :param event_file: The events to simulate.
    """
    events = pickle.load(open(event_file, 'rb'))
    for _, _, event_body in events:
        listener._cb_event(event_body, mock.Mock())
