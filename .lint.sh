#!/bin/bash
set -e
echo "* calling pyflakes"
pyflakes ./src/
echo "* calling pylint"
pylint -E ./src/publisher/** --load-plugins=pylint_django --disable=E1103
echo "* passed linting"
