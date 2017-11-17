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
Openstack connection class.
"""
import os
import time

from landscaper.common import LOG


# Instructional not configurable.
NOVA_API_VERSION = "2"
CINDER_API_VERSION = "2"
NEUTRON_API_VERSION = "2"
HEAT_API_VERSION = "1"
SESSION_TIMEOUT = 3600

# Environment variable names.
OS_USERNAME = "OS_USERNAME"
OS_PASSWORD = "OS_PASSWORD"
OS_AUTH_URL = "OS_AUTH_URL"
OS_TENANT_ID = "OS_TENANT_ID"
OS_TENANT_NAME = "OS_TENANT_NAME"


class OpenStackClientRegistry(object):
    """
    Manages openstack connection details and clients.
    """
    def __init__(self):
        self.token_timestamp = 0
        self.session_timestamp = 0
        self.keystone = None
        self.session = None

    def get_nova_v2_client(self):
        """
        Return a nova, version 2 client.
        """
        from novaclient import client as nova
        return nova.Client(NOVA_API_VERSION, session=self._session())

    def get_cinder_v2_client(self):
        """
        Returns a cinder, version 2 client.
        """
        from cinderclient import client as cinder
        return cinder.Client(CINDER_API_VERSION, session=self._session())

    def get_neutron_v2_client(self):
        """
        Returns a neutron, version 2 client.
        """
        from neutronclient.v2_0 import client as neutron
        return neutron.Client(session=self._session())

    def get_heat_v1_client(self):
        """
        Returns a heat, version 1 client.
        """
        from heatclient import client as heat_client
        return heat_client.Client(HEAT_API_VERSION, session=self._session())

    def _session(self):
        """
        Manages the session for the client registry. If a session expires, a
        new session is created.
        :return: A keystone Session object.
        """
        now = time.time()
        if (now - self.session_timestamp) > SESSION_TIMEOUT:
            self.session = _get_session_keystone_v2()
            self.session_timestamp = now
        return self.session


def _get_session_keystone_v2():
    """
    Returns a keystone session variable.
    """
    from keystoneauth1 import session
    from keystoneauth1.identity import v2
    user, password, auth_uri, project_name = _get_connection_info()
    auth = v2.Password(username=user, password=password,
                       tenant_name=project_name, auth_url=auth_uri)
    return session.Session(auth=auth)


def _get_connection_info():
    """
    Details to enable a connection to an openstack instance.  The Details are
    read from environment variables which are used with the openstack cli
    commands.
    """
    user = os.environ.get(OS_USERNAME)
    password = os.environ.get(OS_PASSWORD)
    auth_uri = os.environ.get(OS_AUTH_URL)
    tenant_name = os.environ.get(OS_TENANT_NAME)
    _check_conn_variables(user, password, auth_uri, tenant_name)
    return user, password, auth_uri, tenant_name


def _check_conn_variables(user, password, auth_uri, tenant_name):
    """
    Check that the environment variables have been found.  Without connection
    variables to the openstack testbed it is impossible to build a landscape
    any openstack components and so an exception is thrown.
    :param user: Username.
    :param password: Password.
    :param auth_uri: URI to the Openstack testbed.
    :param tenant_id: Tenant id.
    :param tenant_name: Tenant Name.
    """

    if not user or not password or not auth_uri or not tenant_name:
        envs = [OS_USERNAME, OS_PASSWORD, OS_TENANT_NAME, OS_TENANT_ID,
                OS_AUTH_URL]
        msg = "Environment variables {e[0]}, {e[1]}, {e[2]}, {e[3]} " \
              "and {e[4]} are required".format(e=envs)
        LOG.error(msg)
        raise ValueError(msg)
