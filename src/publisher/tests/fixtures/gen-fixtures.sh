#!/bin/bash
set -xuv
scraper=/home/luke/dev/python/bot-lax-adaptor
home=$(pwd)

function scrape {
    cd $scraper
    target=$1
    shift # pop first arg
    fname_list="$@" # consume all/rest of args
    for fname in $fname_list
    do
       for path in ./article-xml/articles/$fname*
       do
         ./scrape-article.sh "$path" > $home/$target/${path##*/}.json
       done
    done
    cd -
}

scrape ajson elife-16695- elife-01968- elife-20125- elife-20105- elife-12215-v1
scrape relatedness elife-04718-v1 elife-13038-v1 elife-13620-v1
