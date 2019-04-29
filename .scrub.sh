#!/bin/bash
# scrub.sh uses the autopep8 tool to clean up whitespace and other small bits

black src/ --target-version py34
