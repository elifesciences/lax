#!/bin/bash
source install.sh > /dev/null

control_c() {
    echo "interrupt caught, exiting. this script can be run multiple times ..."
    exit $?
}

trap control_c SIGINT

if [ ! -d .elife-json ]; then
    git clone https://github.com/elifesciences/elife-article-json/ .elife-json
else
    cd .elife-json
    git reset --hard
    git pull
    cd ..
fi
./src/manage.py import .elife-json/article-json/ --import-type eif
