#!/bin/bash

while ! nc -z neo4j 7474; do sleep 10; done
python landscaper.py