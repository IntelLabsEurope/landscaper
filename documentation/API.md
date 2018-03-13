## GET /graph

This request retrieves all living nodes in the landscape at a certain point in time. If no
 timestamp is supplied then the current living nodes are returned.

|  Query parameter | values | default | Description  |
|---|---|---|---|
|  timestamp | Time in seconds since the epoch  | current time | Retrieve the living nodes at this time. |
| timeframe (deprecated)  | Time in seconds since the epoch  | 0 |  Retrieve only nodes that were living from timestamp to timestamp + timeframe. |
|  geo | true, false, 1, 0  | false| Retrieves a geoJSON Feature Collection for all nodes in the query result with geoJSON attributes. |

## GET /subgraph/[node-id]

Returns a subgraph from the landscape, starting from the [node-id] and traversing downwards.

|  Query parameter | values | default | Description  |
|---|---|---|---|
|  timestamp | Time in seconds since the epoch  | current time | Retrieve the living nodes at this time. |
| timeframe (deprecated)  | Time in seconds since the epoch  | 0 |  Retrieve only nodes that were living from timestamp to timestamp + timeframe. |
| geo | true, false, 1, 0 | false | Retrieves a geoJSON Feature Collection for all nodes in the query result with geoJSON attributes. |

## GET /node/[node-id]

Returns a node from the landscape.

|  Query parameter | values | default | Description  |
|---|---|---|---|
|  geo | true, false, 1, 0  | false| Retrieves a geoJSON Feature Collection for all nodes in the query result with geoJSON attributes. |

## PUT /coordinates

Saves a geojson attribute to a node. The bdy of the request should contain a
list of nodes and their geojson geometry objects in the following format:

```
[{'id': <node-id>, 'geo': <geoJSON geometry object>}, {'id': <node-id>, 'geo': <geoJSON geometry object>}, ...]

```
#### Example
```
[{'id': 'machine-A', 'geo': { "type": "LineString", "coordinates": [[0, 0], [10, 10]] }}]
```
