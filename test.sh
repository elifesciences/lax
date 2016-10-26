#!/bin/bash
set -e
. install.sh
. download-api-raml.sh
. .lint.sh
. .test.sh
