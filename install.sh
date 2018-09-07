#!/bin/bash
set -e # everything must succeed.
echo "[-] install.sh"

. download-api-raml.sh

if [ ! -e "venv/bin/python3" ]; then
    echo "could not find venv/bin/python3, recreating venv"
    rm -rf venv
    python3 -m venv venv
fi

source venv/bin/activate

# 'python' becomes whatever python3 system is pointing to

if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

pip install -r requirements.txt --no-cache-dir
NEW_RELIC_EXTENSIONS=false pip install --no-binary :all: newrelic==2.82.0.62

python src/manage.py migrate --no-input

echo "[✓] install.sh"
