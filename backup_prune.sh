#!/bin/bash
set -e

# lsh@2022-03-09: delete any backup files.
rm -f /tmp/lax-db-jenkins-prod-lax-*.json.gz

# lsh@2022-03-09: this now prunes the ubr backup log created in backup.sh
keep=${1:-3}
line_to_start_from=$(echo "${keep}"+1 | bc)

files_to_delete=$(find /tmp -name 'lax-db-*' -printf "%T %p\n" | sort -r | tail -n "+$line_to_start_from" | awk '{ print $2 }')
if [ -n "${files_to_delete}" ]; then
    rm "${files_to_delete}"
fi

