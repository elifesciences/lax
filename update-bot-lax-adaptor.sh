#!/bin/bash
set -e

default_folder="/opt/bot-lax-adaptor"
folder="${1-$default_folder}"
cd $folder
git fetch
git checkout master
git pull origin master
sha1=$(git rev-parse HEAD) 
cd -
echo $sha1 > bot-lax-adaptor.sha1

