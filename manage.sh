#!/bin/bash
set -e

# @description convenience wrapper around Django's runserver command
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

# this starts to reinstall everything in production everytime an article is ingested:

skip_install=$1
if test "$skip_install" != "--skip-install"; then
    echo "installing"
    source install.sh > /dev/null
else
    echo "not installing"
    shift # like 'pop' but for positional args
fi

source venv/bin/activate
./src/manage.py $@
