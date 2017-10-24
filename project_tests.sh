#!/bin/bash
set -e

source venv/bin/activate

. .lint.sh
. .test-green.sh
. .cc-check.sh
