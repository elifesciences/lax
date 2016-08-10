#!/bin/bash
source install.sh

control_c() {
    echo "interrupt caught, exiting. this script can be run multiple times ..."
    exit $?
}

trap control_c SIGINT

./src/manage.py import $1 --import-type eif
