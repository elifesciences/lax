#!/bin/bash
set -e

tag=${1:-latest}

./manage.sh --skip-install dumpdata --exclude=contenttypes --natural-foreign --natural-primary --indent=4 | gzip -9 - > "/tmp/lax-db-${tag}.json.gz"
