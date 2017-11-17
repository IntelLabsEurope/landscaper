# Landscaper

1. [Introduction](#introduction)
2. [Installation](#installation)
	* [Retrieve the code](#retrieve-the-code)
	* [Install Python Packages](#install-python-packages)
	* [Install Neo4j](#install-neo4j)
	* [Configure Landscaper](#configure-landscaper)
3. [Running the Landscaper](#running-the-landscaper)
   	* [Start the Landscaper](#start-the-landscaper)
   	* [Start the REST API](#start-the-rest-api)
   	* [Querying the Landscape](#querying-the-landscape)
4. [Creating a Landscape](#creating-a-landscape)
	* [Collecting Hardware and CPU Information](#collecting-hardware-and-cpu-information)
	* [Collecting OpenStack Information](#collecting-openstack-information)
	* [Flushing the Neo4j Database](#flushing-the-neo4j-database)
5. [About Landscaper](#about-landscaper)

## Introduction

The landscaper constructs a graph describing a computing infrastructure. The graph details what software stacks are running on what virtual infrastructure, and on what physical infrastructure the virtual infrastructure is running.

The data within the landscape is collected via collectors and event listeners. Collectors are provided for physical hardware information (via the output of hwloc and cpuinfo) and for OpenStack environments. Event Listeners are provided for OpenStack.

## Installation

### Retrieve the code

	# Clone the repository 
	git clone https://github.com/IntelLabsEurope/landscaper.git
	# Change directory to the landscaper root.
	cd landscaper
	
### Install python packages

    pip install -r requirements.txt
    
Note that on Ubuntu 16.04.03 LTS, various errors may arise which may be resolved with

    sudo apt-get install libssl-dev libcurl4-openssl-dev
    sudo pip install -r requirements.txt

### Install Neo4j
Follow the neo4j installation manual: https://neo4j.com/docs/operations-manual/current/installation/

The landscaper has been tested against neo4j Community Edition 3.0.9.

Once installed, and with the  neo4j service started, navigate to http://localhost:7474. This is neo4j's graphical browser. Set a username and password. Make note of these credentials, as they will need to be configured in the landscaper configuration file, landscaper.cfg.

> The landscaper has a pluggable architecture to allow the graph to be persisted to any database. Neo4j is the initial backend supported.

### Configure Landscaper

Update the file landscaper.cfg with the appropriate user and password for neo4j.

## Running the Landscaper
The landscaper/data directory contains raw files which the landscaper collectors use to construct a landscape.
By default, the landscaper comes with sample files that define a simple two node cluster.

### Start the Landscaper
From the top level landscaper directory run:

    python landscaper.py

The landscaper physical host and physical network collectors parse relevant files in landscaper/data and construct an appropriate landscape in the neo4j database. 

The landscape can be browsed using the neo4j web browser. 

The sample landscape includes some components at the physical layer. To create a more detailed cloud infrastructure landscape see section ["Creating a Landscape"](#creating-a-landscape) below.

### Start the REST API

Set the python path to the landscaper directory. From the top level landscaper directory run:
 
    export PYTHONPATH=`pwd`

Run the webserver.

    cd landscaper/web
    gunicorn -w 2 application:APP

This will start a webserver running on the localhost at port 8000

### Querying the Landscape

The project contains a samples folder which contains example queries for the Landscaper. These queries can be run on the default example landscape. From the top level landscaper directory run:

    export PYTHONPATH=`pwd`
    cd samples
    python query_landscaper_test.py
    
The command will return a list of the physical machines in the landscape. 
Additional sample queries are visible within query_landscaper_test.py

## Creating a Landscape
### Collecting Hardware and CPU Information
Hardware and CPU information can be collected for each physical machine in your landscape.

Execute the following commands on each machine to be included in the landscape, and copy the output files to the data directory of the landscaper.

	hwloc-ls --of xml > $HOSTNAME"_hwloc.xml"
	cat /proc/cpuinfo > $HOSTNAME"_cpuinfo.txt"

The landscaper.cfg should be updated so that machines lists all HOSTNAMES that are to be landscaped:

	machines=HOSTNAME1,HOSTNAME2,HOSTNAME3

### Collecting OpenStack Information
Set the following OpenStack environment variables as appropriate for your OpenStack environment:

	export OS_TENANT_NAME=
	export OS_PROJECT_NAME=
	export OS_TENANT_ID=
	export OS_USERNAME=
	export OS_PASSWORD=
	export OS_AUTH_URL=

The openstack collectors listen for events from the OpenStack event rabbitMQ queue.  This can be configured in landscaper.cfg by setting the following configuration variables.
	
	[rabbitmq]
	rb_name=
	rb_password=
	rb_host=
	rb_port=
	topic=
	notification_queue=
	exchanges=	

### Flushing the Neo4j Database
To purge all information from the landscape, in the landscaper.cfg file change 
	Flush=False
to
	Flush=True

WARNING: This will delete all data in the Neo4j Database.

## About Landscaper

The landscaper was developed by Intel Labs Europe and is published under the Apache License, Version 2.0.

Contributions from the community are welcome via Pull Requests.