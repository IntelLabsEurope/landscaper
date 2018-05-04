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

from os import path
import sys
import requests
from landscaper.collector import base
from landscaper.collector.physical_host_collector import HWLocCollector
from landscaper.common import LOG
from landscaper import paths
from landscaper.utilities import configuration

CONFIG_SECTION_GENERAL = 'general'
CONFIG_CIMI_URL = "cimi_url"

CONFIG_SECTION_PHYSICAL = 'physical_layer'
CONFIG_VARIABLE_MACHINES = 'machines'

class CimiPhysicalCollector(base.Collector):
    """
    Physical Layer collector that queries CIMI for hwloc and cpu_info files and
    saves files in the Data Directory.
    """
    def __init__(self, graph_db, conf_manager, events_manager, events=None):
        super(CimiPhysicalCollector, self).__init__(graph_db, conf_manager,
                                                events_manager, events=None)
        self.cnf = conf_manager

    def init_graph_db(self):
        """
        Retrieve hwloc and cpu_info for each machine and add
        files to the Data Directory.
        """
        LOG.info("Generating hwloc and cpu_info files")
        devices_list = list()

        for device in self.get_devices():
            if self.generate_files(device) :
                devices_list.append(device["id"][7:]) #eg, device/737fe63b-2a34-44fe-9177-3aa6284ba2f5

        # write the device list to the config file
        device_csv = ','.join(str(x) for x in devices_list)
        LOG.info("CIMI device list: " + device_csv)
        self.conf_manager.set_variable(CONFIG_SECTION_PHYSICAL, CONFIG_VARIABLE_MACHINES, device_csv)

    def update_graph_db(self, event, body):
        """
        Save the hwloc and cpuinfo files to be picked up by the physical collector.
        """
        if event=="ADD":
            self.generate_files(body)

        elif event == "DELETE":
            raise NotImplementedError # yet!

    def generate_files(self, device):
        """
        Queries the hwloc and cpuinfo methods and writes them to a file
        :param device: model_mf2c.classes.Device used to query the hwloc and cpu_info methods
        :return: True if file successfully save, False if errors encountered
        """
        try:
            cpu_path = path.join(paths.DATA_DIR, device["id"][7:] + "_cpuinfo.txt")
            cpu_info = device["cpuinfo"]
            if cpu_info is None:
                LOG.error("CPU_info data has not been set for this device: " + device.id + ". No CPU_info file will be saved.")
                return False
            self._write_to_file(cpu_path, cpu_info)

            hwloc_path = path.join(paths.DATA_DIR, device["id"][7:] + "_hwloc.xml")
            hwloc = device["hwloc"]
            if hwloc is None:
                LOG.error(
                    "hwLoc data has not been set for this device: " + device.id + ". No HwLoc file will be saved.")
                return False
            self._write_to_file(hwloc_path, hwloc)

        except:
            LOG.error("General Error hwloc/cpuinfo for device id: " + device.id, sys.exc_info()[0])
            return False
        return True

    # returns all instances of devices
    def get_devices(self):
        try:
            cimi_url = self.cnf.get_variable(CONFIG_SECTION_GENERAL, CONFIG_CIMI_URL)
            if cimi_url is None:
                LOG.error("'CIMI_URL' has not been set in the 'general' section of the config file")
                return
            res = requests.get(cimi_url + '/device',
                               headers={'slipstream-authn-info': 'super ADMIN'},
                               verify=False)

            if res.status_code == 200:
                return res.json()['devices']

            LOG.error("Request failed: " + res.status_code)
            LOG.error("Response: " + str(res.json()))
            return None
        except:
            LOG.error('Exception', sys.exc_info()[0])
            return None

    @staticmethod
    def _write_to_file(filename, file_content):
        """
        Creates file, writes to file, saves  and closes file
        :param filename: file name including file path
        :param file_content: string content for file
        """
        file_handler = open(filename, "w")
        file_handler.write(file_content)
        file_handler.close()

if __name__ == "__main__":
    #from landscaper.utilities import configuration
    conf_manager = configuration.ConfigurationManager()
    conf_manager.add_section('physical_layer')
    conf_manager.add_section('general')

    dut = CimiPhysicalCollector(None, conf_manager,None, None)
    LOG.info(dut.init_graph_db())
