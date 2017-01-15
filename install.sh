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
        virtualenv --python=`which python3` venv
    fi
fi
source venv/bin/activate
if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi
pip install -r requirements.txt
python src/manage.py migrate --no-input
