#!/bin/bash
# clones/updates the elife api-raml repository
# this repository contains the specification for article-json and
# is used to validate what the scraper generates.
# see `src/validate.py`

set -e # everything must pass
mkdir -p schema
cd schema
if [ ! -d api-raml ]; then
    git clone https://github.com/elifesciences/api-raml
fi
cd ..

if [ -f api-raml.sha1 ]; then
    cd schema/api-raml
    git reset --hard
    git checkout "$(cat ../../api-raml.sha1)"
    #if type node > /dev/null; then
    #    # if node is installed, like on a dev machine recompile
    #    # the api as lax uses the contents of the dist dir.
    #    node compile.js
    #fi
    cd -
fi
