# Coordinates

1. [Parsing GeoJSON file](#parsing-geojson-file)
2. [Storing the geolocation through the Landscaper API](#storing-the geolocation-through-the-landscaper-api)
3. [Requesting GeoJSON FeatureCollection](#requesting-geojson-featurecollection)
4. [Manually testing geoJSON API](#manually-testing-geojson-api)


## Parsing GeoJSON file

The method coordinates.load_coordinates() loads GeoJSON coordinates from coordinates file stored in data/coordinates.json

The coordinates file is expected to follow the established format http://geojson.org/

The method coordinates.component_coordinates() takes a machine ID as an input and parses the GeoJSON file and returns the associated geometry object.

### Example
GeoJSON file
```
{
  "type" : "FeatureCollection",
  "features":[
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [125.6, 10.1]
      },
      "properties": {
        "name": "Dinagat Islands"
      }
    }
  ]
}
```
 Calls to component_coordinates returns the geometry object.
```
from landscaper.utilities import coordinates


coords = coordinates.component_coordinates("Dinagat Islands")
```
This returns:
```
{
  "type": "Point",
  "coordinates": [125.6, 10.1]
}
```

## Storing the geolocation through the Landscaper API

The method application.put_geolocation() uses a HTTP PUT method to store the geolocation of the nodes to the database using the Landscaper API.

The application.put_geolocation() accesses the request data containing the parsed GeoJSON file. The machine ID, the dictionary containing the type and coordinates and the current time are inputted into graph_db.update node().
The graph_db.update_node() method saves and expires the previous geoloation while updating the node with the current location. If the node does not exist or does not hold coordinate data the method will return an error and abort the task.

The method returns a '200 OK' if all nodes have been updated successfully with the current geolocation data. If there is incomplete geolocation data the function returns an error, specifying the problematic node ID.  

### Example
Run the Landscaper API
```
cd landscaper/web
export PYTHONPATH=`pwd`
gunicorn w -2 application.py
```

While the web service is running call:
http://localhost:9001/coordinates

Successful update returns:
```
200 OK
```

## Requesting GeoJSON FeatureCollection

The following landscaper methods have been altered to take an optional URL parameter (geo=True or geo=False, or the usual combinations of lower-case, 0, 1 etc.):
```
/graph
/subgraph
/node
```

### graph
To test the graph method, use the following URL:
```
http://localhost:9001/graph
```
### subgraph
To test the subgraph method:
```
http://localhost:9001/subgraph/nodeId?geo=true
```
### node
To test an individual node:
```
http://localhost:9001/node/nodeId?geo=true
```
## Manually testing geoJSON API

To start a local landscaper with some Geojson data in it, go to test/test_utils and run start_server_geo.py

This starts a landscaper on port 9001 and with regular graph, subgraph etc. methods.

### graph
To test the graph method, use the following URL:
```
http://localhost:9001/graph?geo=True
```

### subgraph
To test the subgraph method:
```
http://localhost:9001/subgraph/nodeId?geo=true
```

With the test data inserted by setup_server_geo.py:
```
http://localhost:9001/subgraph/nodey1?geo=true
```

### node
With the test data inserted by setup_server_geo.py:
```
http://localhost:9001/node/nodey1?geo=true
```
