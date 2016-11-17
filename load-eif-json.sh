#!/bin/bash
set -e

. ./install.sh

control_c() {
    echo "interrupt caught, exiting. this script can be run multiple times ..."
    exit $?
}

trap control_c SIGINT

./manage.sh import $1 --import-type eif
