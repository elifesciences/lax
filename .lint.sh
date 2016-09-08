#!/bin/bash
set -e
echo "* calling pylint"
pylint -E ./src/publisher/** --load-plugins=pylint_django --disable=E1103
echo "* calling pyflakes"
pyflakes ./src/
echo "* passed linting"
