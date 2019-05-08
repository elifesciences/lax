#!/bin/bash
# scrub.sh uses the autopep8 tool to clean up whitespace and other small bits

if [ -e venv/bin/python3.6 ]; then
    black src/ --target-version py34
else
    # seeing this on new 16.04 lax instances
    echo "black requires Python 3.6+"
fi
