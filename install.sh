#!/bin/bash
set -e # everything must succeed.

. download-api-raml.sh

# use the latest version of python2 we can find.

# ll: /usr/bin/python2.7
maxpy=$(which /usr/bin/python2* | grep -E '[0-9]$' | sort -r | head -n 1)

# ll: python2.7
# http://stackoverflow.com/questions/2664740/extract-file-basename-without-path-and-extension-in-bash
py=${maxpy##*/} # magic

# check for exact version of python
if [ ! -e "venv/bin/$py" ]; then
    echo "rebuilding venv"
    rm -rf venv
    virtualenv --python="$maxpy" venv
else
    echo "found venv/bin/$py"
fi
source venv/bin/activate
if [ ! -e app.cfg ]; then
    echo "* no app.cfg found! using the example settings (elife.cfg) by default."
    ln -s elife.cfg app.cfg
fi
pip install -r requirements.txt
python src/manage.py migrate --no-input
