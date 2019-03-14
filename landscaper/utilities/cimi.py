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
import requests
from landscaper.common import LOG
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings()

CONFIG_SECTION_GENERAL = 'general'
CONFIG_CIMI_URL = "cimi_url"
CIMI_SEC_HEADERS = {"slipstream-authn-info:internal ADMIN"}
SSL_VERIFY = False

class CimiClient():

    def __init__(self, conf_manager):
        self.cnf = conf_manager
        cimi_url = self.cnf.get_variable(CONFIG_SECTION_GENERAL, CONFIG_CIMI_URL)
        if cimi_url is None:
            LOG.error("'CIMI_URL' has not been set in the 'general' section of the config file")
            return
        # TODO: certificate authentication issues
        if cimi_url.lower().find('https') > 0:
            requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

        self.cimi_url = cimi_url

    # returns events by default, delete events.
    def get_events(self, from_date=None, event_type="DELETED", limit=None):
        # try:
        date_filter = ""
        if from_date:
            date_filter = '&$filter=created>"%s"' % from_date
        limit_filter = ""
        if limit:
            limit_filter = "&$last={}".format(limit)
        url = self.cimi_url + '/event?$orderby=created:desc$filter=content/state="' + event_type + '"' + date_filter + limit_filter
        # print url
        res = requests.get(url,
                           headers={'slipstream-authn-info': 'internal ADMIN'},
                           verify=SSL_VERIFY)

        if res.status_code == 200:
            return res.json()

        LOG.error("Request failed: " + str(res.status_code))
        LOG.error("Response: " + str(res.json()))
        return dict()

    # returns a specific device
    def get_collection(self, collection, from_date=None, limit=None):
        # try:
        date_filter = ""
        if from_date:
            date_filter = '&$filter=created>"%s"' % from_date
        limit_filter = ""
        if limit:
            limit_filter = "&$last={}".format(limit)
        url = self.cimi_url + '/' + collection + '?$orderby=created:desc' + date_filter + limit_filter
        # print url
        res = requests.get(url,
                           headers={'slipstream-authn-info': 'internal ADMIN'},
                           verify=SSL_VERIFY)

        if res.status_code == 200:
            return res.json()

        LOG.error("Request failed: " + str(res.status_code))
        LOG.error("Response: " + str(res.json()))
        return dict()


