#!/bin/bash

# everything must pass
set -e

# reload the virtualenv
rm -rf venv/
. mkvenv.sh
source venv/bin/activate
pip install -r requirements.txt

# upgrade all deps to latest version
pip install pip-review
pip-review --pre # preview the upgrades
echo "[any key to continue ...]"
read -p "$*"
pip-review --auto --pre # update everything
