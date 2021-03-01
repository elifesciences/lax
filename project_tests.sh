#!/bin/bash
set -e

exit 1

source venv/bin/activate

. .lint.sh
. .test.sh
. .cc-check.sh
