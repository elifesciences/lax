#!/bin/bash
set -e # everything must succeed.
if [ ! -d venv ]; then
    virtualenv --python=`which python2` venv
fi
source venv/bin/activate

pip install -r requirements.txt
python src/manage.py migrate
