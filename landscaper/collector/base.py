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
Base Class for a collector.
"""
import abc
import os


class Collector(object):
    """
    Parent class for a collector. The parent requires all children to have
    initialisation and update methods.
    """
    def __init__(self, graph_db, conf_manager, events_manager, events=None):
        self.events_manager = events_manager
        self.graph_db = graph_db
        self.conf_manager = conf_manager
        events = events or []
        self._subscribe_to_events(events)

    def _subscribe_to_events(self, events):
        """
        Registers events with the events manager, so that the events listener
        is listening fro updates.
        :param events: Events to listen for.
        """
        for event in events:
            self.events_manager.subscribe_to_event(event, self)

    @staticmethod
    def get_installation_dir():
        """
        Finds a collectors directory.
        """
        return os.path.dirname(os.path.abspath(__file__))

    @abc.abstractmethod
    def init_graph_db(self):
        """
        This method is called when the landscape is first being created. Each
        collector uses this method to grab all of the resources that they are
        collecting and then adds them to the landscape.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def update_graph_db(self, event, body):
        """
        This method is called by the event listener when it gets a notification
        from an event which is our collector has subscribed to. The event type
        and event message are passed in as arguments.
        :param event: Event Type.
        :param body: Event Message.
        """
        raise NotImplementedError
