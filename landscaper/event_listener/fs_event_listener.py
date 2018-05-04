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
File System change listener.
"""
import asyncore
import pyinotify
from landscaper import paths
from landscaper.common import LOG
from landscaper.event_listener import base

# watched events
EVENTS_MASK = pyinotify.IN_DELETE | pyinotify.IN_CREATE
EVENTS = [pyinotify.IN_DELETE,
          pyinotify.IN_CREATE]


class FsEventListener(base.EventListener, pyinotify.ProcessEvent):
    """
    Listener implementation for the /data directory to add new hosts
    """
    def __init__(self, events_manager, conf):
        super(FsEventListener, self).__init__(events_manager)
        self.register_events(EVENTS)
        self.wm = pyinotify.WatchManager()  # Watch Manager

    def listen_for_events(self):
        """
        Listen for new files added to /data directory
        """
        pyinotify.AsyncNotifier(self.wm, self)
        self.wm.add_watch(paths.DATA_DIR, EVENTS_MASK, rec=True)
        asyncore.loop()

    # pyinotify.ProcessEvent methods
    def process_IN_CREATE(self, event):
        LOG.info("Triggering event: %s", event.pathname)
        self.events_manager.dispatch_event(pyinotify.IN_CREATE, event.pathname)

    def process_IN_DELETE(self, event):
        LOG.info("Triggering event: %s", event.pathname)
        self.events_manager.dispatch_event(pyinotify.IN_DELETE, event.pathname)
