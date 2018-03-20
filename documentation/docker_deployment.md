## Landscaper Docker Deployment

### Prior to Setup
1. Install docker and docker-compose.
2. The landscaper/data directory contains files which the landscaper collectors use to construct a landscape. By default, the landscaper comes with sample files that define a simple two node cluster. Otherwise the host machine needs access to the data directory. Prior to setup, copy the data directory and configuration file to a location on the host machine.
For Example:

```
home
├── landscaper_folder
      ├── landscaper.cfg
      ├── data
```

3. Update landscaper.cfg on the host machine with the appropriate user and password for neo4j.
4. To access neo4j from the container, change the neo4j URL from http://localhost:7474/db/data to http://neo4j:7474/db/data

### Building the Image

Run the following commands to build the images:
```
sudo docker build -f base/Dockerfile -t landscaper_base .
sudo docker build -f landscaper/Dockerfile -t landscaper .
sudo docker build -f landscaper_api/Dockerfile -t landscaper_web .
```

### Changes to docker-compose files
1. If Neo4j is already installed on your host machine, change the host port from 7474 to another available port (HOST_PORT:CONTAINER_PORT).
```
ports:
  - 17474:7474
```

2. Enter the location of the data directory and landscaper.cfg file.
```
volumes:
 - /home/landscaper_folder/data:/landscaper/data
 - /home/landscaper_folder/landscaper.cfg:/landscaper/landscaper.cfg
```

### Start the Landscaper and Neo4j Containers
```
sudo docker-compose up
```
Web API is accessible at http://localhost:9001.
