#!/bin/bash

set -e # everything must pass

echo "[-] .test-green.sh"

pyflakes src/

args="$@"
module="src"
print_coverage=1
coverage_threshold=80

if [ ! -z "$args" ]; then
    # we're running a subset of tests
    module="src.$args"
    # suppress coverage report
    print_coverage=0
fi

# remove any old compiled python files
find src/ -name '*.pyc' -delete

GREEN_CONFIG=.green LAX_MULTIPROCESSING=1 ./src/manage.py test "$module" \
    --testrunner=green.djangorunner.DjangoRunner \
    --no-input \
    -v 3
echo "* passed tests"

# run coverage test
# only report coverage if we're running a complete set of tests
if [ $print_coverage -eq 1 ]; then
    coverage report
    # is only run if tests pass
    covered=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
    if [ $covered -lt $coverage_threshold ]; then
        echo
        echo "FAILED this project requires at least $coverage_threshold% coverage, got $covered%"
        echo
        exit 1
    fi
fi

echo "[✓] .test-green.sh"
