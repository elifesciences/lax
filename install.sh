#!/bin/bash
set -e # everything must succeed.

. download-api-raml.sh

if [ ! -d venv ]; then
    virtualenv --python=`which python3` venv
else
    # check for old python2 binary
    if [ -e venv/bin/python2 ]; then
        echo "old python2 venv detected, rebuilding venv"
        rm -rf venv
        # use the latest version of python3 we can find. 
        # on Ubuntu14.04 the stable version is 3.3, the max we can install is 3.6
        maxpy3=$(which /usr/bin/python3* | grep -E '[0-9]$' | sort -r | head -n 1)
        virtualenv --python="$maxpy3" venv
    fi
fi
source venv/bin/activate
if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi
pip install -r requirements.txt
python src/manage.py migrate --no-input
