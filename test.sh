#!/bin/bash
set -e
. install.sh
. .lint.sh
. .test.sh
# encoding errors in python3 version of xenon/radon
#. .cc-check.sh
