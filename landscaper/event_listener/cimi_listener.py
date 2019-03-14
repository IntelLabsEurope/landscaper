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

import os
import json
from landscaper.common import LOG
from landscaper.event_listener import base
from landscaper.utilities.cimi import CimiClient
import time

CIMI_LISTENER_INTERVAL_SECS = 5
CIMI_SEC_HEADERS = "slipstream-authn-info:internal ADMIN"
CIMI_TYPES = ['device']
CIMI_CRUD_EVENTS = ['create', 'delete']

# INIT - create events and subscribe, initialize a dictionary for each device to store last run dates,
#        urls for additions. For deletions, just one url
# JOB - One request each for all adds, One request for all deletes.
class CimiListener(base.EventListener):

    def __init__(self, events_manager, configuration_manager):
        super(CimiListener, self).__init__(events_manager)
        if self.events_manager:
            cimi_events = events()
            self.register_events(cimi_events)
            self.create_from_dates = {}
            self.cimiClient = CimiClient(configuration_manager)

    def get_data(self, cimi_type):
        json_data = {}
        # creates
        return self.cimiClient.get_collection(cimi_type, self.create_from_dates.get(cimi_type))

    def listen_for_events(self):
        LOG.info("Subscribing to CIMI events")
        while True:
            if 'create' in CIMI_CRUD_EVENTS:
                for cimi_type in CIMI_TYPES:
                    data = self.cimiClient.get_collection(cimi_type, from_date=self.create_from_dates.get(cimi_type))
                    event = 'cimi.'+cimi_type+'.'+'create'
                    self.raise_events(event, data)
            if 'delete' in CIMI_CRUD_EVENTS:
                cimi_type = 'event'
                data = self.cimiClient.get_events(from_date=self.create_from_dates.get(cimi_type), event_type="DELETED")
                event = 'cimi.' + cimi_type + '.' + 'delete'
                self.raise_events(event, data)
            time.sleep(CIMI_LISTENER_INTERVAL_SECS)

    def raise_events(self, event, data):
        collection = event.split('.')[1]
        prev_date = self.create_from_dates.get(collection)
        events = data.get(collection + 's')
        if events and len(events) > 0:
            events.sort(key=cimi_sort, reverse=True)
            self.create_from_dates[collection] = events[0]["created"]
        else:
            # print "No events received for {}".format(event)
            return
        if not prev_date:
            return
        if 'create' in event:
            for new_item in events:
                LOG.info("CIMI Create Event : {}".format(new_item))
                self.dispatch(event, new_item)
        if 'delete' in event:
            for deleted_item in events:
                LOG.info("CIMI Delete Event : {}".format(deleted_item))
                href = deleted_item['content']['resource']['href']
                collection = href.split('/')[0]
                delete_event = 'cimi.'+collection+'.delete'
                self.dispatch(delete_event, href)


def events():
    evts = []
    for cimi_type in CIMI_TYPES:
        for crud_event in CIMI_CRUD_EVENTS:
            evt = 'cimi.'+cimi_type+'.'+crud_event
            evts.append(evt)
    return evts

def cimi_sort(obj):
    return obj['created']
