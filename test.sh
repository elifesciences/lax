#!/bin/bash
set -e
source install.sh
pylint -E ./src/publisher/** --load-plugins=pylint_django --disable=E1103
echo "* passed linting"
coverage run --source='src/' src/manage.py test src/
echo "* passed tests"
coverage report