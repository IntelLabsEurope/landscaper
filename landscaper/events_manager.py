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
Events Manager class.
"""

from landscaper.common import LOG


class EventsManager(object):
    """
    Connects events to collectors that have subscribed to the event. Events are
    first registered with the manager and then collectors can subscribe to
    events they would like to be notified of.
    """
    def __init__(self):
        self.events = dict()

    def register_event(self, event):
        """
        Register an event with the Events Manager. Adds an event to a list of
        events that are to be managed.
        :param event: Event name.
        """
        if event not in self.events:
            self.events[event] = list()

    def subscribe_to_event(self, event, collector):
        """
        A collector subscribes to an event, so that it will be notified once an
        event occurs.
        :param event: Event name.
        :param collector: Collector class.
        """
        if event not in self.events:
            LOG.error("Unknown event: %s. Not Registered.", event)
        else:
            if collector not in self.events.get(event):
                self.events.get(event).append(collector)

    def dispatch_event(self, event, event_body=None):
        """
        This method is called once an event occurs. Then event is then
        dispatched to all collectors which have previously subscribed to the
        event.
        :param event: Name of the event.
        :param event_body: Event details.
        """
        for subscriber in self.events.get(event, list()):
            subscriber.update_graph_db(event, event_body)
