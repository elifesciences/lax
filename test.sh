#!/bin/bash
source install.sh > /dev/null
# enable once pylint+pylint-django are working again
pylint -E ./src/publisher/** --load-plugins=pylint_django --disable=E1103
echo "passed linting"
./src/manage.py test src/
