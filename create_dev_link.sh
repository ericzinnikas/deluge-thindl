#!/bin/bash
cd /home/ericz/projects/deluge-thindl/thindl
mkdir temp
export PYTHONPATH=./temp
/home/ericz/projects/deluge-thindl/env/bin/python setup.py build develop --install-dir ./temp
cp ./temp/thindl.egg-link /home/ericz/.config/deluge/plugins
rm -fr ./temp
