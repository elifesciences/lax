#!/bin/bash
source install.sh
cd src/core/
ln -s dev_settings.py settings.py
cd ../../
python src/manage.py migrate
source test.sh
