#!/bin/bash
set -e

echo "[-] .lint.sh"

# remove any old compiled python files
# pylint likes to lint them
find src/ -name '*.py[c|~]' -delete
find src/ -regex "\(.*__pycache__.*\|*.py[co]\)" -delete

echo "pyflakes"
pyflakes ./src/

echo "pylint"
# E1103 - a variable is accessed for a nonexistent member, but astng was not able to interpret all possible types of this variable.
pylint -E ./src/publisher/** --load-plugins=pylint_django \
    --disable=E1103 2> /dev/null
# specific warnings we're interested in, comma separated with no spaces
# presence of these warnings are a failure
pylint ./src/publisher/** --load-plugins=pylint_django \
    --disable=all --reports=n --score=n \
    --enable=redefined-builtin,pointless-string-statement,no-else-return,redefined-outer-name

echo "scrubbing"
. .scrub.sh 2> /dev/null

echo "[✓] .lint.sh"
