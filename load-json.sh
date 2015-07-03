#!/bin/bash
set -e
. venv/bin/activate
./src/manage.py import_article $1
