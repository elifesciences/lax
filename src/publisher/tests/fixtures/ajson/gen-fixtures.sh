#!/bin/bash
set -xuv
home=$(pwd)
cd /home/luke/dev/python/bot-lax-adaptor
for fname in elife-16695- elife-01968- elife-20125- elife-20105- elife-12215-v1
do
   for path in ./article-xml/articles/$fname*
   do
     ./scrape-article.sh "$path" > $home/${path##*/}.json
   done
done

