#!/bin/bash
set -e

echo "[-] .lint.sh"

# pylint likes to lint them
find src/ -name '*.py[c|~]' -delete
find src/ -regex "\(.*__pycache__.*\|*.py[co]\)" -delete

echo "pyflakes"
pyflakes ./src/
# disabled until pylint supports Python 3.6
# https://github.com/PyCQA/pylint/issues/1113

echo "pylint"
pylint -E ./src/publisher/** --load-plugins=pylint_django --disable=E1103
# specific warnings we're interested in, comma separated with no spaces
# presence of these warnings are a failure
pylint ./src/publisher/** --load-plugins=pylint_django --disable=all --reports=n --score=n \
    --enable=redefined-builtin

echo "scrubbing"
. .scrub.sh

echo "[✓] .lint.sh"
