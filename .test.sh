#!/bin/bash

set -e

pyflakes src/

args="$@"
module="src"
print_coverage=1
if [ -n "$args" ]; then
    module="$args"
    print_coverage=0
fi

# remove any old compiled python files that interfere with test discovery and test artifacts
find src/ -name '*.pyc' -delete
rm -f build/junit.xml

# testing management commands that require a queue shared between processes
export DJANGO_SETTINGS_MODULE=core.settings
export LAX_MULTIPROCESSING=1

# run the tests
if [ $print_coverage -eq 0 ]; then
    # a *specific* test file or test has been given, don't bother with coverage et al
    pytest "$module" -vvv
else
    pytest "$module" -vvv --cov=src --cov-config=.coveragerc --junitxml=build/junit.xml --override-ini junit_family=xunit1
    coverage report

    # only run if tests pass
    covered=$(coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
    if [ "$covered" -lt 80 ]; then
        echo
        echo "FAILED this project requires at least 80% coverage, got $covered"
        echo
        exit 1
    fi
fi

echo "[✓] .test.sh"
