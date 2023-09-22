#!/bin/bash
set -e

# lax requires api-raml to exist before it can start.
. download-api-raml.sh

. mkvenv.sh

source venv/bin/activate

if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

pip install pip wheel --upgrade
pip install -r requirements.txt

python src/manage.py migrate --no-input
