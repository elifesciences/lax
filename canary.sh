#!/bin/bash

# everything must pass
set -e

# stop if settings file missing
if [ ! -f src/core/settings.py ]; then
    echo "no settings.py found. quitting while I'm ahead."
    exit 1
fi

# reload the virtualenv
rm -rf venv/
virtualenv --python=`which python3.5` venv
source venv/bin/activate
pip install -r requirements.txt

# upgrade all deps to latest version
pip install pip-review
pip-review --pre # preview the upgrades
echo "[any key to continue ...]"
read -p "$*"
pip-review --auto --pre # update everything

# run the tests
python src/manage.py migrate
./src/manage.py test src/
