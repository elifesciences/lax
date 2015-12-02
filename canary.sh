#!/bin/bash
set -e
if [ ! -f src/core/settings.py ]; then
    echo "no settings.py found. quitting while I'm ahead."
    exit 1
fi
rm -rf venv/
virtualenv --python=`which python2` venv
source venv/bin/activate
pip install -r requirements.txt
pip install pip-review
pip-review --pre
echo "[any key to continue ...]"
#read -p "$*"
pip-review --auto --pre
echo "results"
pip-review --pre --verbose
#read -p "$*"
python src/manage.py migrate
source test.sh
