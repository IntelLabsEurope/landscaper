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
Event listener base class.
"""
import abc
import os
import threading


class EventListener(threading.Thread):
    """
    Base Class for an Events listener.
    """
    def __init__(self, events_manager):
        self.events_manager = events_manager
        super(EventListener, self).__init__()
        self.daemon = True

    @abc.abstractmethod
    def listen_for_events(self):
        """
        Waits for events; once an event is received then the dispatch event
        method should be called to deal with the event.
        """
        raise NotImplementedError

    def run(self):
        """
        Once the thread is run then the abstract method is called, to listen
        on events.
        """
        self.listen_for_events()

    def dispatch(self, event, body=None):
        """
        Dispatches any received even to the events manager to push it to
        subscribed collectors.
        :param event: Received event type.
        :param body: Event message.
        """
        self.events_manager.dispatch(event, body)

    def register_events(self, events):
        """
        Registers the events which the listener receives with the events
        manager.
        """
        for event in events:
            self.events_manager.register_event(event)

    @staticmethod
    def get_installation_dir():
        """
        Finds a listener's directory.
        """
        return os.path.dirname(os.path.abspath(__file__))
