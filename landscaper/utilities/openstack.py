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
#
# Authors:
# KeystoneAuth v3 compatibility added by : Frank Griesinger (frank.griesinger@uni-ulm.de)
#
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
OS_PROJECT_ID = "OS_PROJECT_ID"
OS_PROJECT_NAME = "OS_PROJECT_NAME"
OS_USER_DOMAIN_NAME = "OS_USER_DOMAIN_NAME"
OS_TENANT_ID = "OS_TENANT_ID"
OS_TENANT_NAME = "OS_TENANT_NAME"


class OpenStackClientRegistry(object):
    """
    Manages openstack connection details and clients.
    """
    def __init__(self):
        self.token_timestamp = 0
        self.session_timestamp = 0
        auth_uri = os.environ.get(OS_AUTH_URL)
        keystone_ver = '2'
        if auth_uri.lower().replace('/', '').endswith('v3'):
            keystone_ver = '3'
        self.keystone_ver = keystone_ver
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
            if self.keystone_ver == '3':
                self.session = _get_session_keystone_v3()
            else:
                self.session = _get_session_keystone_v2()
            self.session_timestamp = now
        return self.session


def _get_session_keystone_v2():
    """
    Returns a keystone session variable.
    """
    from keystoneauth1 import session
    from keystoneauth1.identity import v2
    user, password, auth_uri, project_name, project_id, user_domain_name = _get_connection_info('2')
    auth = v2.Password(username=user, password=password,
                       tenant_name=project_name, auth_url=auth_uri)
    return session.Session(auth=auth)


def _get_session_keystone_v3():
    """
    Returns a keystone session variable.
    """
    from keystoneauth1.identity import v3
    from keystoneauth1 import session
    from keystoneclient.v3 import client

    user, password, auth_uri, project_name, project_id, user_domain_name = _get_connection_info('3')

    auth = v3.Password(auth_url=auth_uri,
                    username=user,
                    password=password,
                    project_id=project_id,
                    user_domain_name=user_domain_name
                    )
    envs = [user, password, auth_uri, project_name, project_id, user_domain_name]
    msg = "AUTH with user ({e[0]}), password (****), auth_uri ({e[2]}), " \
          " project_name ({e[3]}), project_id ({e[4]}) " \
          "and user_domain_name ({e[5]}).".format(e=envs)
    LOG.info(msg)
    sess = session.Session(auth=auth)

    return sess;
def _get_connection_info(keystone_ver):
    """
    Details to enable a connection to an openstack instance.  The Details are
    read from environment variables which are used with the openstack cli
    commands.
    """
    user = os.environ.get(OS_USERNAME)
    password = os.environ.get(OS_PASSWORD)
    auth_uri = os.environ.get(OS_AUTH_URL)
    project_name = os.environ.get(OS_PROJECT_NAME)
    project_id = os.environ.get(OS_PROJECT_ID)
    user_domain_name = os.environ.get(OS_USER_DOMAIN_NAME)
    _check_conn_variables(user, password, auth_uri, project_name, project_id, user_domain_name, keystone_ver)
    return user, password, auth_uri, project_name, project_id, user_domain_name
def _check_conn_variables(user, password, auth_uri, project_name, project_id, user_domain_name, keystone_ver):
    """
    Check that the environment variables have been found.  Without connection
    variables to the openstack testbed it is impossible to build a landscape
    any openstack components and so an exception is thrown.
    :param user: Username.
    :param password: Password.
    :param auth_uri: URI to the Openstack testbed.
    :param project_name: Tenant Name.
    :param project_id: Project ID.
    :param user_domain_name: User domain name.
    """

    envs = [OS_USERNAME, OS_PASSWORD, OS_PROJECT_NAME, OS_PROJECT_ID, OS_AUTH_URL, OS_USER_DOMAIN_NAME]
    msg = ""
    if keystone_ver == '3':
        #print [user, password, auth_uri, project_name, project_id, user_domain_name]
        if not user or not password or not auth_uri or not project_name or not project_id or not user_domain_name:
            msg = "Environment variables {e[0]}, {e[1]}, {e[2]}, {e[3]}, {e[4]} " \
                  "and {e[5]} are required".format(e=envs)
    else:
        #print [user, password, auth_uri, project_name]
        if not user or not password or not auth_uri or not project_name:
            msg = "Environment variables {e[0]}, {e[1]}, {e[2]} and {e[3]} are required".format(e=envs)
    if len(msg) > 0:
        LOG.error(msg)
        raise ValueError(msg)
