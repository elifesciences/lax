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
scrape v12/api2 elife-21393-v1
scrape relatedness elife-04718-v1 elife-13038-v1 elife-13620-v1
scrape ppp2 elife-00353-v1 elife-00385-v1 elife-01328-v1 elife-02619-v1 elife-03401- elife-03665-v1 elife-06250-
scrape ppp2 elife-07301-v1 elife-08025- elife-09571-v1
