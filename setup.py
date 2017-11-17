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

from distutils.core import setup

setup(name='landscaper',
      version='1.0',
      description='Creates a live landscape for a cloud infrastructure.',
      author='Intel Labs Europe',
      packages=['landscaper'],
      requires=['py2neo==3.1.2', 'networkx==1.11', 'kombu==4.1.0',
                'pycurl==7.43.0', 'rfc3986==0.4.1', 'flask==0.12.1',
                'keystoneauth1==2.18', 'pythoncinderclient==1.11.0',
                'pythonheatclient==1.8.0', 'pythonkeystoneclient==3.10.0',
                'pythonneutronclient==6.1.0',  'pythonnovaclient==7.1.0',
                'gunicorn == 19.7.1'])
