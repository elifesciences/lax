#!/bin/bash
set -e
. venv/bin/activate

control_c() {
    echo "interrupt caught, exiting. this script can be run multiple times ..."
    exit $?
}

trap control_c SIGINT

./src/manage.py import_article $1
