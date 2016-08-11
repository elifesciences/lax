#!/bin/bash
set -e
./install.sh
if [ ! -f aws-perms.sh ]; then
    echo "an 'aws-perms.sh' file not found."
    echo "this file contains the environment variables required for lax to talk to AWS"
    exit 1
fi
# put the vars into ENV
set -a; source aws-perms.sh; set +a
# call the repopulate command
./manage.sh repop
./manage.sh import .repop/ --import-type eif
tar cvzf repop-import.$(date -I).tar.gz .repop/
#rm -rf .repop/
