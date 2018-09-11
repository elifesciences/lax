#!/bin/bash
set -e # everything must succeed.
echo "[-] install.sh"

. download-api-raml.sh

python=''
pybinlist=("python3.6" "python3.5" "python3.4")

for pybin in ${pybinlist[*]}; do
    which "$pybin" &> /dev/null || continue
    python=$pybin
    break
done

if [ -z "$python" ]; then
    echo "no usable python found, exiting"
    exit 1
fi

if [ ! -e "venv/bin/$python" ]; then
    echo "could not find venv/bin/$python, recreating venv"
    rm -rf venv
    $python -m venv venv
else
    echo "using $python"
fi

source venv/bin/activate

if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi

pip install -r requirements.txt --no-cache-dir
NEW_RELIC_EXTENSIONS=false pip install --no-binary :all: newrelic==2.82.0.62

python src/manage.py migrate --no-input

echo "[✓] install.sh"
