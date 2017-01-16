#!/bin/bash
set -exv

# remove any old compiled python files
# pylint likes to lint them
find src/ -name '*.py[c|~]' -delete
find src/ -regex "\(.*__pycache__.*\|*.py[co]\)" -delete

echo "* calling pyflakes"
pyflakes ./src/
# disabled until pylint supports Python 3.6
# https://github.com/PyCQA/pylint/issues/1113
#echo "* calling pylint"
#pylint -E ./src/publisher/** --load-plugins=pylint_django --disable=E1103 2> /dev/null
echo "* scrubbing"
. .scrub.sh 2> /dev/null
