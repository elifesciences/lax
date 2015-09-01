#!/bin/bash
# @description convenience wrapper around Django's runserver command
source install.sh
./src/manage.py $@
