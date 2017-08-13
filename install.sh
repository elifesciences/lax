#!/bin/bash
set -e # everything must succeed.
echo "[-] install.sh"

. download-api-raml.sh

python=/usr/bin/python3.5
py=${python##*/} # ll: python3.5

# check for exact version of python3
if [ ! -e "venv/bin/$py" ]; then
    echo "could not find venv/bin/$py, recreating venv"
    rm -rf venv
    $python -m venv venv
fi

source venv/bin/activate

if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

pip install -r requirements.txt
NEW_RELIC_EXTENSIONS=false pip install --no-binary :all: newrelic==2.82.0.62

python src/manage.py migrate --no-input

echo "[✓] install.sh"
