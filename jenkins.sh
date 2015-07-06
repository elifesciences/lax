#!/bin/bash

set -e      # everything must succeed.

# create a virtualenv if necessary + activate
if [ ! -d venv ]; then
    virtualenv --python=`which python2` venv
fi
. venv/bin/activate

# install project dependencies
pip install -r requirements.txt

python src/manage.py migrate

source test.sh
