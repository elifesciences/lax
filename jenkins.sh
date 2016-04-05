#!/bin/bash
source install.sh
python src/manage.py migrate
source test.sh
