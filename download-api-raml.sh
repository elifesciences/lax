#!/bin/bash
# clones/updates the elife api-raml repository
# this repository contains the specification for article-json and
# is used to validate what the scraper generates.
# see `src/validate.py`

set -e # everything must pass
mkdir -p schema
cd schema
if [ -d api-raml ]; then
    cd api-raml
    git reset --hard
    git pull
    if type node > /dev/null; then
        # if node is installed, like on a dev machine recompile
        # the api as lax uses the contents of the dist dir.
        node compile.js
    fi
    cd ..
else
    git clone https://github.com/elifesciences/api-raml --depth 1
fi
cd ..
