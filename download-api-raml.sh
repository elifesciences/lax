#!/bin/bash
# clones/updates the elife api-raml repository
# this repository contains the specification for article-json and
# is used to validate what the scraper generates.
# see `src/validate.py`
set -e # everything must pass

echo "[-] download-api-raml.sh"

mkdir -p schema
(
    cd schema
    if [ ! -d api-raml ]; then
        git clone https://github.com/elifesciences/api-raml
    fi
)

if [ -f api-raml.sha1 ]; then   
    sha="$(cat api-raml.sha1)"
    (
        cd schema/api-raml/
        git reset --hard
        git fetch
        git checkout "$sha"

        # lsh@2021-08-24: disabling this. it was necessary during development but not anymore.
        # when testing against unreleased api-raml, the `./dist` directory hasn't 
        # been updated. if we're not working within /srv/lax, re-compile the api-raml
        _=$(pwd != /srv/lax);
        recompile=$?

        recompile=1

        if [ "$recompile" = "0" ]; then
            if type node 2> /dev/null; then
                # if node is installed, like on a dev machine recompile
                # the api as lax uses the contents of the dist dir.
                npm install
                node compile.js
            fi
        fi
    )
fi

echo "[✓] download-api-raml.sh"
