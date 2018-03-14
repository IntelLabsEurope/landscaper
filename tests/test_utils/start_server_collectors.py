import landscaper.web.application
from tests.test_utils import utils
from landscaper import landscape_manager
import time

IDENTITY_ATTR = {'layer': 'virtual', 'type': 'vm', 'category': 'compute'}
STATE_ATTR = {'vcpu': None, 'mem': None, 'geo': None}

utils.create_test_config()
manager = landscape_manager.LandscapeManager(utils.TEST_CONFIG_FILE)
graph_db = manager.graph_db

geom1 = { "type": "Point", "coordinates": [-0.016284317471172, 51.543000257676]}
geom2 = {"type": "Point", "coordinates": [-0.016384317471172, 51.553000257676]}
geom3 = {    'type': 'Polygon',
    'coordinates': [[[-0.016284317471172, 51.5503000257676],
                     [-0.017284317471172, 51.5483000257676],
                     [-0.011384317471172, 51.543000257676],
                     [-0.010884317471172, 51.540000257676],
                     [-0.012884317471172, 51.540000257676],
                     [-0.0160284317471172, 51.5483000257676],
                     [-0.016284317471172, 51.5503000257676]
    ]]}

timestamp = int(time.time())

state1 = STATE_ATTR.copy()
state1['geo'] = geom1
state2 = STATE_ATTR.copy()
state2['geo'] = geom3

graph_db.delete_all()
id_node1 = graph_db.add_node("nodey1", IDENTITY_ATTR, state1, timestamp)
id_node2 = graph_db.add_node("nodey2", IDENTITY_ATTR, state2, timestamp)

landscaper.web.application.APP.run(port=9001)