#!/bin/bash

set -e # everything must pass

echo "[-] .test-green.sh"

pyflakes src/

args="$@"
module="src"
if [ ! -z "$args" ]; then
    module="src.$args"
fi

# remove any old compiled python files
find src/ -name '*.pyc' -delete

# called by test.sh
rm -f build/junit.xml

GREEN_CONFIG=.green LAX_MULTIPROCESSING=1 ./src/manage.py test "$module" \
    --testrunner=green.djangorunner.DjangoRunner \
    --no-input \
    -v 3

echo "[✓] .test-green.sh"
