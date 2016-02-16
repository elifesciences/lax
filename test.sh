#!/bin/bash
source install.sh > /dev/null
# enable once pylint+pylint-django are working again
pylint -E ./src/publisher/** --load-plugins=pylint_django --disable=E1103
echo "* passed linting"
coverage run --source='src/' src/manage.py test src/
echo "* passed tests"
coverage report