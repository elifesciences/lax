#!/bin/bash
set -e # everything must succeed.
if [ ! -d venv ]; then
    virtualenv --python=`which python2` venv
fi
source venv/bin/activate
if [ ! -f src/core/settings.py ]; then
    print "no settings.py found. quitting while I'm ahead."
    exit 1
fi
pip install -r requirements.txt
python src/manage.py migrate
