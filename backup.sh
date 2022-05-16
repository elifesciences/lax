#!/bin/bash
set -e

tag=${1:-latest}

# lsh@2022-03-09: disabled. files being generated were incomplete and therefore useless as backups.
#./manage.sh --skip-install dumpdata --exclude=contenttypes --natural-foreign --natural-primary --indent=4 | gzip -9 - > "/tmp/lax-db-${tag}.json.gz"

# ~70mins as of 2022-03-09
#  ~4mins as of 2022-05-11
cd /opt/ubr && sudo DESCRIPTOR_DIR=/etc/ubr-alt ./ubr.sh | tee "/tmp/lax-db-jenkins-prod-lax-${tag}.log"
