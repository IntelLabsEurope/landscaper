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
""""
Tests for the Openstack utilities module
"""
import unittest
import mock
from os import environ
from landscaper.utilities import openstack

v3uri = "http://localhost:35357/v3/"
v2uri = "http://localhost:35357/v2.0/"
#v2uri = "http://10.1.22.3:5000/v2.0"

class TestOpenStack(unittest.TestCase):
    def setUp(self):
        self.user = "admin"
        self.password = "ADMIN_PASS"
        self.project_name = "default"
        self.project_id = "default"
        self.user_domain_name = "default"
        # set environment variables
        environ["OS_USERNAME"] = self.user
        environ["OS_PASSWORD"] = self.password
        environ["OS_PROJECT_NAME"] = self.project_name
        environ["OS_PROJECT_ID"] = self.project_id
        environ["OS_USER_DOMAIN_NAME"] = self.user_domain_name

    def test__session(self):
        # test for url matching version : v3
        environ["OS_AUTH_URL"] = v3uri
        os = openstack.OpenStackClientRegistry()
        session = os._session()
        assert (session is not None), "Session for v3 auth is not created: " + v3uri

        # test for url matching version : v2
        environ["OS_AUTH_URL"] = v2uri
        os = openstack.OpenStackClientRegistry()
        session = os._session()
        assert (session is not None), "Session for v2 auth is not created: " + v2uri
