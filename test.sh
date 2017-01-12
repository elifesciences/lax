#!/bin/bash
set -e
. install.sh
. .lint.sh
. .test.sh
. .cc-check.sh
