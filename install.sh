#!/bin/bash
set -e # everything must succeed.
echo "[-] install.sh"

. download-api-raml.sh

. mkvenv.sh

source venv/bin/activate

if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

pip install -r requirements.txt --no-cache-dir
NEW_RELIC_EXTENSIONS=false pip install --no-binary :all: newrelic==2.82.0.62

python src/manage.py migrate --no-input

echo "[✓] install.sh"
