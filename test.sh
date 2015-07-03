#!/bin/bash
set -e
. venv/bin/activate
./src/manage.py test src/
