#!/bin/bash
set -e
source test.sh
coverage html
firefox htmlcov/index.html
