#!/bin/bash
source install.sh > /dev/null

control_c() {
    echo "interrupt caught, exiting. this script can be run multiple times ..."
    exit $?
}

trap control_c SIGINT

if [ ! -d .elife-json ]; then
    git clone https://github.com/elifesciences/elife-article-json/ .elife-json
fi
./src/manage.py import_article .elife-json/article-json/
rm -rf ./.elife-json/
