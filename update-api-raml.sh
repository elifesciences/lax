#!/bin/bash
set -e

./download-api-raml.sh
cd schema/api-raml
git fetch
git rev-parse origin/master > ../../api-raml.sha1
cd -
./download-api-raml.sh

