#!/bin/bash
set -e

keep=${1:-3}
line_to_start_from=$(echo ${keep}+1 | bc)

files_to_delete=$(find /tmp -name 'lax-db-*' -printf "%T %p\n" | sort -r | tail -n "+$line_to_start_from" | awk '{ print $2 }')
rm $files_to_delete
