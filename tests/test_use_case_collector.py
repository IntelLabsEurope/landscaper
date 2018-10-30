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
Tests for UseCase Collector
"""
import os

import unittest
import mock

from landscaper.collector import use_case_collector
from landscaper.collector import base


class TestUseCase(unittest.TestCase):
    """
    Unit tests for UseCase Collector to load a landscape into the Landscaper.
    """
    def setUp(self):
        self.conf_mock = mock.Mock()
        self.ucc = use_case_collector.UseCaseCollector(None,
                                                       self.conf_mock,
                                                       None, None)

    def test_update_graph_db_call(self):
        """
        Test to check error raised when attempting to call update graph method.
        """
        self.assertRaises(NotImplementedError, self.ucc.update_graph_db, None, None)

    def test_inheritance(self):
        """
        Check that TestUseCase class is inherited from base class
        :return:
        """
        self.assertIsInstance(self.ucc, base.Collector)

    @mock.patch("landscaper.collector.use_case_collector.paths")
    @mock.patch("landscaper.collector.use_case_collector.os.remove")
    @mock.patch("landscaper.collector.use_case_collector.pyexcel")
    def test_use_case_collector(self, mck_pyexcel, mck_os_remove, mck_path):
        """
        Test to check functionality of the use case collector
        :param mck_pyexcel
        :param mck_os_remove
        :param mck_path
        """
        mck_path.DATA_DIR = "tests/data"
        self.ucc._create_cpuinfo_file.return_value = mock.Mock()
        self.ucc._search_links.return_value = mock.Mock()
        self.ucc._add_network_switch.return_value = mock.Mock()

        self.ucc.init_graph_db()

        mck_os_remove.assert_any_call("tests/data/fake_cpuinfo.txt")
        mck_pyexcel.get_sheet.assert_any_call(file_name="tests/data/nodes.csv",
                                              name_columns_by_row=0)
        mck_pyexcel.get_sheet.assert_any_call(file_name="tests/data/links.csv",
                                              name_columns_by_row=0)

    @mock.patch("landscaper.collector.use_case_collector.paths")
    def test_hwloc_created(self, mck_path):
        """
        Test hwloc is created and modifications amended to file
        :param mck_path:
        """
        mck_path.DATA_DIR = "/lola/manola"
        mck_write = mock.Mock()
        self.ucc._build_hwloc_object = mock.Mock()
        self.ucc._build_hwloc_object.return_value = ('mac', mck_write)

        self.ucc._create_hwloc_file("potatoe", 11)
        mck_write.write.assert_called_with('/lola/manola/potatoe-11_hwloc.xml')

    @mock.patch("landscaper.collector.use_case_collector.paths")
    def test_build_hwloc_object(self, mck_path):
        """
        Test build hwloc file
        :param mck_path:
        """
        mck_path.TEMP_HWLOC = "tests/data/fake_hwloc.xml"
        _, obj = self.ucc._build_hwloc_object("FAKE_NODE", 40)
        infos = obj.findall("object/info")

        self.assertEqual(len(infos), 2)
        self.assertEqual(infos[0].get('name'), "SKIP")
        self.assertEqual(infos[0].get('value'), "WRONG_VALUE")
        self.assertEqual(infos[1].get('name'), "HostName")
        self.assertEqual(infos[1].get('value'), "FAKE_NODE-40")

    @mock.patch("landscaper.collector.use_case_collector.shutil")
    @mock.patch("landscaper.collector.use_case_collector.paths")
    @mock.patch("landscaper.collector.use_case_collector.os.rename")
    def test_copy_rename_cpuinfo(self, mck_os_rename, mck_path, mck_shutil):
        """
        Test copy and rename the cpuinfo file into the data directory
        :param mck_shutil:
        :param mck_path:
        :param mck_os_rename:
        """
        mck_path.TEMP_CPUINFO = "tests/data/fake_cpuinfo.txt"
        mck_path.DATA_DIR = "tests/data"
        self.ucc._create_cpuinfo_file("FAKE_NODE", 40)
        mck_shutil.copy.assert_called_with("tests/data/fake_cpuinfo.txt",
                                           "tests/data")
        mck_os_rename.assert_called_with('tests/data/template_cpuinfo.txt',
                                         'tests/data/FAKE_NODE-40_cpuinfo.txt')

    @mock.patch("landscaper.collector.use_case_collector.paths")
    @mock.patch("landscaper.collector.use_case_collector.yaml")
    @mock.patch("landscaper.collector.use_case_collector.open")
    def test_add_switch(self, mck_open, mck_yaml, mck_path):
        """
        Test add network switch data to the network description yaml file
        :param mck_open:
        :param mck_yaml:
        :param mck_path:
        """
        mck_path.NETWORK_DESCRIPTION = "fake/path"
        mck_open.return_value.__enter__.return_value = 'fake_file_handler'

        fake_node = ["CLFAR", "Network", "Switch", 2,
                     "Faraday", "Core"]
        fake_attrib = ["SAUID", "Category", "Type", "Num of Servers",
                       "Exchange", "Tier"]
        fake_link = [1, 2, 3]
        expected_switch = {'CLFAR': {'address': 'clfar',
                                     'connected-devices': [1, 2, 3],
                                     'SAUID': 'CLFAR',
                                     'Tier': 'Core',
                                     'Exchange': 'Faraday'}}

        self.ucc._add_network_switch(fake_node, fake_attrib, fake_link)
        mck_yaml.safe_dump.assert_called_with(expected_switch,
                                              'fake_file_handler',
                                              default_flow_style=False)

    @mock.patch("landscaper.collector.use_case_collector.paths")
    def test_link_search(self, mck_path):
        """
        Test the link search function and saves the correct connection
        for each switch
        :param mck_path:
        """
        mck_path.DATA_DIR = "tests/data"
        fake_links = [['network1', 'network2'], ['network2', 'network3'],
                      ['network3', 'network1'], ['network4', 'network1']]
        new_connection = self.ucc._search_links(fake_links, 'network1')

        self.assertEqual(len(new_connection), 2)
        self.assertEqual(new_connection, ['network3', 'network4'])