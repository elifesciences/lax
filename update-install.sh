#!/bin/bash

set -e      # everything must succeed.

#git pull    # update the Lax repo

# create a virtualenv if necessary + activate
if [ ! -d venv ]; then
    virtualenv --python=`which python2` venv
fi
. venv/bin/activate

# install project dependencies
pip install -r requirements.txt

python src/manage.py migrate
