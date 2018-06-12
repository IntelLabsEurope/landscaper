#!/bin/bash
# wait for neo4j

neo_host=$1

echo $neo_host

sleep 4
while ! curl -f $neo_host; do sleep 1; done
echo "---found neo4j"
sleep 8
echo "starting landscaper"
python landscaper.py