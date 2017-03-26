#!/bin/bash
set -e

source venv/bin/activate

. .lint.sh
. .test.sh
. .cc-check.sh
