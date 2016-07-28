#!/bin/bash

set -e

# remove any old compiled python files
find src/ -name '*.pyc' -delete

# called by test.sh
rm -f build/junit.xml
coverage run --source='src/' --omit='*/tests/*,*/migrations/*' src/manage.py test src/ --no-input
echo "* passed tests"

coverage report

# is only run if tests pass
covered=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
if [ $covered -lt 65 ]; then
    echo
    echo "FAILED this project requires at least 65% coverage, got $covered"
    echo
    exit 1
fi

