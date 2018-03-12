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
Main module for the landscaper. Initialises everything and starts the
landscaper.
"""
import importlib
import os
import time

from landscaper import common
from landscaper import paths
from landscaper import events_manager
from landscaper.utilities import configuration

CONFIGURATION_SECTION = 'general'


class LandscapeManager(object):
    """
    Initilises all components of the landscaper and then starts the landscaper.
    The landscape manager is the main entry point into the landscaper.
    """
    def __init__(self, config_file=paths.CONF_FILE):
        self.conf_manager = configuration.ConfigurationManager(config_file)
        self.conf_manager.add_section(CONFIGURATION_SECTION)
        self.events_manager = events_manager.EventsManager()

        # Initilise plugins.
        self.graph_db = None
        self.collectors = []
        self.listeners = []
        self.state = "inactive"

        self._instantiate_graph_db()

    def start_landscaper(self):
        """
        Starts the landscape.  If flush is set to true in the config file then
        the entire database is tore down and rebuilt.
        """
        self._initialise_landscaper()
        if self.conf_manager.get_flush():
            self.state = "building"
            self.graph_db.delete_all()
            self._initilise_graph_db()
        self._start_listeners()

    def status(self):
        """
        Returns the status of the landscaper.
        """
        return self.state

    def _initialise_landscaper(self):
        self._instantiate_event_listeners()
        self._instantiate_collectors()

    def _instantiate_event_listeners(self):
        """
        Instantiate all listeners which were set in the config file.
        """
        event_listeners = self.conf_manager.get_event_listeners()
        plugin_parameters = [self.events_manager, self.conf_manager]
        self.listeners = self._load_plugins(event_listeners,
                                            common.EVENT_LISTENER_PACKAGE,
                                            paths.EVENT_LISTENER_DIR,
                                            plugin_parameters)

    def _instantiate_graph_db(self):
        """
        Instantiate the graph database.
        """
        graph_db_name = self.conf_manager.get_graph_db()
        plugin_parameters = [self.conf_manager]
        self.graph_db = self._load_plugins([graph_db_name],
                                           common.GRAPH_PACKAGE,
                                           paths.GRAPH_DB_DIR,
                                           plugin_parameters)[0]

    def _instantiate_collectors(self):
        """
        Instantiate all collectors which were set in the config file.  A list
        of collectors is set. These are ordered the same as in the config file
        and the order is important.
        """
        collectors = self.conf_manager.get_collectors()
        plugin_params = [self.graph_db, self.conf_manager, self.events_manager]
        self.collectors = self._load_plugins(collectors,
                                             common.COLLECTOR_PACKAGE,
                                             paths.COLLECTOR_DIR,
                                             plugin_params)

    def _initilise_graph_db(self):
        """
        Builds the graph database by calling the initilise method of all of the
        collectors in order.
        """
        for collector in self.collectors:
            collector.init_graph_db()

    def _start_listeners(self):
        """
        Starts all of the listeners listening.
        """
        if self.listeners:
            self.state = "listening"
            for event_lister in self.listeners:
                event_lister.start()
            while True:
                # Todo: look into joining the threads. Issue #45
                time.sleep(1)

    @staticmethod
    def _load_plugins(plugin_names, package, plugin_dir, plugin_params=None):
        """
        Searches in a package for all plugins specified in the plugin_names
        list and then instantiates these plugins with the plugin_params. We
        search for plugins, rather than specifying so that plugins can be added
        more easily.
        :param plugin_names: List of plugin class names. These classes must
        exist in a module of the specified package.
        :param package: The package where the plugins reside.
        :param plugin_dir: Plugin directory.
        :param plugin_params: List of parameters which are passed in to the
        constructor of the plugin.
        """
        plugins = []
        for plugin_name in plugin_names:
            for file_name in os.listdir(plugin_dir):
                if file_name.endswith(".py"):
                    module_name = '.' + file_name.rstrip(".py")
                    module = importlib.import_module(module_name, package)
                    plugin_class = getattr(module, plugin_name, None)
                    if plugin_class:
                        plugins.append(plugin_class(*plugin_params))
                        break  # Only one plugin per module.
        return plugins
