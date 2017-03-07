#!/bin/bash
set -e

# @description convenience wrapper around Django's runserver command
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR

skip_install=$1
if test "$skip_install" = "--skip-install"; then
    shift # like 'pop' but for positional args
else
    source install.sh > /dev/null
fi

source venv/bin/activate
./src/manage.py $@
