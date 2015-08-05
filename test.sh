#!/bin/bash
source install.sh > /dev/null
./src/manage.py test src/
