#!/bin/bash
set -e # everything must succeed.
if [ ! -d venv ]; then
    virtualenv --python=`which python2` venv
fi
source venv/bin/activate
if [ ! -f src/core/settings.py ]; then
    #echo "no settings.py found. if this is a dev environment you can do 'ln -s dev_settings.py settings.py' in the src/core/ directory. Quitting."
    #exit 1
    echo "no settings.py found! using the DEV settings (dev_settings.py) by default."
    cd src/core/
    ln -s dev_settings.py settings.py
    cd ../../
fi
pip install -r requirements.txt
python src/manage.py migrate
