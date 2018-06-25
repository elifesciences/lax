#!/bin/bash

set -e # everything must pass

echo "[-] .test-green.sh"

#pyflakes src/

args="$@"
module="src"
if [ ! -z "$args" ]; then
    module="src.$args"
fi

GREEN_CONFIG=.green LAX_MULTIPROCESSING=1 ./src/manage.py test "$module" \
    --testrunner=green.djangorunner.DjangoRunner \
    --no-input \
    -v 3

echo "[✓] .test-green.sh"
