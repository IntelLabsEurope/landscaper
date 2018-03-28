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

3. Update landscaper.cfg on the host machine with the appropriate user and password for neo4j. This must be different to the default neo4j/neo4j user/pass.
4. To configure access neo4j from the container, change the port of the neo4j URL in landscaper.cfg from http://localhost:7474/db/data (the port chosen should match the one used in the docker-compose file for neo4j 7475 in the example below)

### Building the Image

From the landscaper/docker directory run the following command to build the images:
```
docker-compose build
```
(Optional)If required the individual images can be built as follows:
```
sudo docker build -f base/Dockerfile -t landscaper_base .
sudo docker build -f landscaper/Dockerfile -t landscaper .
sudo docker build -f landscaper_api/Dockerfile -t landscaper_web .
```

### Changes to docker-compose files
1. Enter a location to store the neo4j data (replace <local_path>).
```
neo4j:
  image: neo4j:3.0
  volumes:
   - <local_path>/neo4j_data:/data
```
2. If Neo4j is already installed on your host machine or port 7474 is otherwise unavailable, change the host port from 7474 to another available port (HOST_PORT:CONTAINER_PORT).
```
ports:
  - 7475:7474
```
3. Set the neo4j username/password it should match the params set in landscaper.cfg
```
environment:
   - NEO4J_AUTH=neo4j/password

```
4. Under the landscaper section enter the location of the data directory and landscaper.cfg file. (replace <local_path>)
```
 landscaper:
  build: ./landscaper
  image: landscaper:latest
  volumes:
   - <local_path>/landscaper/data:/landscaper/data
   - <local_path>/landscaper/landscaper.cfg:/landscaper/landscaper.cfg
```
5. If integrating with an openstack installation you will need to set several environment variables the landscaper section to allow access.
```
environment:
    - OS_TENANT_NAME=
    - OS_PROJECT_NAME=
    - OS_TENANT_ID=
    - OS_USERNAME=
    - OS_PASSWORD=
    - OS_AUTH_URL=
```
6. Under the web section enter the location of the landscaper.cfg file (replace <local_path>)
```
web:
  build: ./landscaper_api
  image: landscaper_web:latest
  volumes:
   - <local_path>/landscaper/landscaper.cfg:/landscaper/landscaper.cfg
```


### Start the Landscaper and Neo4j Containers
```
sudo docker-compose up
```
Web API is accessible at http://localhost:9001

The neo4j interface will be at http://localhost:7475

In default configuration a simple cypher query to neo4j should return the example 2 node landscape
```
match (n) return n
```

