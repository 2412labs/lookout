#!/bin/bash
: ${1?must provide path to log directory}
cd "$(dirname "$0")"
mkdir -p $1
python3 -u cameraThingExample.py -c conf.json 2>&1 | svlogd -tt $1 
