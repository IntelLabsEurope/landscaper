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
from datetime import datetime
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings()

CONFIG_SECTION_GENERAL = 'general'
CONFIG_CIMI_URL = "cimi_url"
CIMI_SEC_HEADERS = {"slipstream-authn-info": "internal ADMIN"}
SSL_VERIFY = False


class CimiClient():

    def __init__(self, conf_manager):
        self.cnf = conf_manager
        cimi_url = self.cnf.get_variable(
            CONFIG_SECTION_GENERAL, CONFIG_CIMI_URL)
        if cimi_url is None:
            LOG.error(
                "'CIMI_URL' has not been set in the 'general' section of the config file")
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
        url = self.cimi_url + '/event?$orderby=created:desc$filter=content/state="' + \
            event_type + '"' + date_filter + limit_filter
        res = requests.get(url,
                           headers=CIMI_SEC_HEADERS,
                           verify=SSL_VERIFY)

        if res.status_code == 200:
            return res.json()

        LOG.error("Request failed: " + str(res.status_code))
        LOG.error("Response: " + str(res.json()))
        return dict()

    # returns a specific device
    def get_collection(self, collection, from_date=None, limit=None, updates=False):
        # try:
        fieldName = "created"
        if updates is True:
            fieldName = "updated"
        date_filter = ""
        if from_date:
            date_filter = '&$filter=' + fieldName + '>"%s"' % from_date
        limit_filter = ""
        if limit:
            limit_filter = "&$last={}".format(limit)
        url = self.cimi_url + '/' + collection + '?$orderby=' + \
            fieldName + ':desc' + date_filter + limit_filter
        # print url
        res = requests.get(url,
                           headers={'slipstream-authn-info': 'internal ADMIN'},
                           verify=SSL_VERIFY)

        if res.status_code == 200:
            return res.json()

        LOG.error("Request failed: " + str(res.status_code))
        LOG.error("Response: " + str(res.json()))
        return dict()

    def add_service_container_metrics(self, id, device_id, start_time):
        url = self.cimi_url + '/service-container-metric'
        data = {'container_id': id, 'device_id': {'href': 'device/'+device_id},
                'start_time': start_time}
        resp = requests.post(url, headers=CIMI_SEC_HEADERS,
                             verify=SSL_VERIFY, json=data)
        if resp.status_code != 201:
            LOG.error(resp.json())
        return resp

    def update_service_container_metrics(self, id, device_id, end_time):
        coll = self.get_collection('service-container-metric')
        coll = coll['serviceContainerMetrics']
        device_id = "device/{0}".format(device_id)
        end_time = float(end_time) // 1000000000
        end_time = datetime.utcfromtimestamp(end_time)
        mlsec = end_time.microsecond
        json_end_time = end_time.strftime(
            '%Y-%m-%dT%H:%M:%S.%f{:02d}Z'.format(mlsec))
        scm_id = None
        for item in coll:
            dev_id = item['device_id']['href']
            cont_id = item['container_id']
            if dev_id == device_id and cont_id == id:
                scm_id = item['id']
                break
        if scm_id:
            url = self.cimi_url + '/' + scm_id
            data = {'stop_time': json_end_time}
            res = requests.put(
                url, headers=CIMI_SEC_HEADERS, verify=SSL_VERIFY, json=data)
            if res.status_code != 200:
                LOG.error(res.json())
            return res
        else:
            return ""
