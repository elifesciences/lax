#!/bin/bash
# @description convenience wrapper around Django's runserver command
source install.sh > /dev/null
./src/manage.py $@
