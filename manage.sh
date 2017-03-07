#!/bin/bash
# @description convenience wrapper around Django's runserver command
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

# this starts to reinstall everything in production everytime an article is ingested:
#source install.sh > /dev/null

source venv/bin/activate
./src/manage.py $@
