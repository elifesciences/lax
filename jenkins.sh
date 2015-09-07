#!/bin/bash
cd src/core/
ln -s dev_settings.py settings.py
cd ../../

source install.sh
python src/manage.py migrate
source test.sh
