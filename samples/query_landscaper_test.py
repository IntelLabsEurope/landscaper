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
Sample queries for the landscaper.
"""
from samples import client

# Retrieve the graph of the landscape in the form of a Networkx
nx_graph = client.get_graph()

# Query 1: Return all physical machines on the landscape
machine_list = client.get_machines(nx_graph)
print "Query 1: Machine List: ", machine_list

# The following queries can be used in OpenStack landscapes.
# The queries return the physical machines hosting a particular VM
# or running a software stack. It can also return the name of a VM
# running a particular software stack.
# To query the landscaper, enter the node name for the VM or
# software stack.

# Query 2: Return physical machine that is running a particular software stack
#host_machine_stack = client.get_host_machine_for_stack(nx_graph, "ENTER_STACK_NAME")
#print "Query 2: Machine ID running software stack is: ", host_machine_stack[0]

# Query 3: Return virtual machine that is running a particular software stack
#host_vm = client.get_vm_running_stack(nx_graph, "ENTER_STACK_NAME")
#print "Query 3: VM ID running software stack is: ", host_vm[0]

# Query 4: Return physical machine ID that is hosting a particular VM
#host_machine = client.get_host_machine_for_vm(nx_graph, "ENTER_VM_NAME")
#print "Query 4: VM is hosted on: ", host_machine[0]

# Query 5: Get a subgraph starting from the specified node
#subgraph_vm2 = client.get_subgraph("ENTER_NODE_NAME")