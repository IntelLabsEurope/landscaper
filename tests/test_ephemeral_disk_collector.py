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
Tests for the nova collector.
"""
import socket
import unittest
import mock
import time
import os
from mock import patch
from landscaper.landscape_manager import LandscapeManager
from tests.test_utils import utils

from paramiko.ssh_exception import NoValidConnectionsError
from paramiko.ssh_exception import AuthenticationException
from landscaper.collector import ephemeral_disk_collector

# W0212 -  Access to a protected member
# pylint: disable=W0212

# Node Structure.
IDENTITY_ATTR = {'layer': 'virtual', 'type': 'vm', 'category': 'compute'}
STATE_ATTR = {'vcpu': None, 'mem': None}

class TestEphemeralDiskRetrieval(unittest.TestCase):
    """
    Unittests for the ephemeral disk methods.
    """
    def setUp(self):
        utils.create_test_config()
        manager = LandscapeManager(utils.TEST_CONFIG_FILE)
        self.graph_db = manager.graph_db
        self.graph_db.delete_all()
        self.conf_manager = manager.conf_manager
        self.conf_manager.add_section('physical_layer')

        confmgr_mock = mock.Mock()
        confmgr_mock.get_types_to_filter.return_value = []
        confmgr_mock.get_machines.return_value = ['machine-A']
        #collector = phc.HWLocCollector(graphdb_mock, confmgr_mock, None)

        self.collector = ephemeral_disk_collector.EphemeralDiskCollector(self.graph_db, self.conf_manager, mock.Mock())#confmgr_mock, mock.Mock())
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        self.xml_file_path = os.path.join(tests_dir, 'data/ephemeral_collector.xml')
        f = open(self.xml_file_path, 'r')
        self.xml_dump = f.read().strip()
        #print("loaded xml file - %s..." % self.xml_dump[:200])

    @patch("landscaper.collector.ephemeral_disk_collector.paramiko")
    @patch("landscaper.collector.ephemeral_disk_collector.LOG")
    def test_no_connection(self, mck_log, mck_paramiko):
        """
        Check that if there is no connection to the hosts that the error is
        handled
        """
        error = {('127.0.0.1', 22): ""}
        connect_mck = mock.Mock(side_effect=NoValidConnectionsError(error))
        mck_paramiko.SSHClient().connect = connect_mck

        ssh_client = self.collector._ssh_client('127.0.0.1')
        self.assertIsNone(ssh_client)
        self.assertTrue(mck_log.error.called)

    @patch("landscaper.collector.ephemeral_disk_collector.paramiko")
    @patch("landscaper.collector.ephemeral_disk_collector.LOG")
    def test_authentication_failure(self, mck_log, mck_paramiko):
        """
        Check that ssh authentication errors are handled.
        """
        connect_mck = mock.Mock(side_effect=AuthenticationException('error'))
        mck_paramiko.SSHClient().connect = connect_mck
        ssh_client = self.collector._ssh_client('127.0.0.1')

        self.assertIsNone(ssh_client)
        self.assertTrue(mck_log.error.called)

    @patch("landscaper.collector.ephemeral_disk_collector.paramiko")
    @patch("landscaper.collector.ephemeral_disk_collector.LOG")
    def test_socket_errors(self, mck_log, mck_paramiko):
        """
        Check that the socket errors are handled.
        """
        connect_mck = mock.Mock(side_effect=socket.error('error'))
        mck_paramiko.SSHClient().connect = connect_mck
        ssh_client = self.collector._ssh_client('127.0.0.1')

        self.assertIsNone(ssh_client)
        self.assertTrue(mck_log.error.called)

    def test_machine_hosts(self):
        # test that a list of machines can be obtained - get from config
        self.assertTrue(self.collector.hosts[0] == 'machine-A')



    def test_instance_disks(self):
        # with xml file already dumped, test the part of _host_ephemeral_disks
        instance_id, instance_disks = self.collector._instance_disks(self.xml_dump)
        print("instance_id = %s, instance_disks =%s" % (instance_id, instance_disks) )
        self.collector.instance_disks[instance_id] = instance_disks

        # testing for return / parsing of XML
        disk1 = instance_disks[0]
        disk2 = instance_disks[1]
        self.assertEquals(disk1[0], "vda")
        self.assertEquals(disk2[0], "vdz")
        now_ts = time.time()
        disk_obj = self.collector.instance_disks[instance_id]

        # must have nodes and edges from nova_collector - so add them in the test
        host = "instance-00002cc1"
        self._add_instance(instance_id, "vcpus", "mem", "name", host, now_ts)
        self.collector.attach_ephemeral_disk_to_instance(instance_id, disk_obj, now_ts)

        # test real graphDB
        vdz_nodes = self.graph_db.get_nodes_by_properties({"name":"194e4602-3c79-43ae-a27f-eed56a69aacd_vdz"})
        vda_nodes = self.graph_db.get_nodes_by_properties({"name": "194e4602-3c79-43ae-a27f-eed56a69aacd_vdz"})
        self.assertEquals(len(vdz_nodes), 1)
        self.assertEquals(len(vda_nodes), 1)



    def _add_instance(self, uuid, vcpus, mem, name, hostname, timestamp):
        """
        Adds a new instance to the graph database.
        :param uuid: Instance id.
        :param vcpus: Number of vcpus.
        :param mem: Size of memory.
        :param name: Instance name.
        :param hostname: Parent host.
        :param timestamp: Epoch timestamp.
        """
        identity, state = self._create_instance_nodes(vcpus, mem, name)
        inst_node = self.graph_db.add_node(uuid, identity, state, timestamp)
        machine = self.collector._get_machine_node(hostname)

        # Creates the edge between the instance and the machine.
        if inst_node is not None and machine is not None:
            label = "DEPLOYED_ON"
            self.graph_db.add_edge(inst_node, machine, timestamp, label)

    def _create_instance_nodes(self, vcpus, mem, name):
        """
        Creates the identity and state node for an instance.  They are created
        using the standard attributes for each instance, identity and state
        node.
        :param vcpus: Number of vcpus on the instance.
        :param mem: Size of memory on the instance.
        :param name: Name of the instance.
        :return: State and instnace nodes.
        """
        identity_node = IDENTITY_ATTR.copy()
        state_node = STATE_ATTR.copy()
        state_node["vcpu"] = vcpus
        state_node["mem"] = mem
        state_node["vm_name"] = name
        return identity_node, state_node




