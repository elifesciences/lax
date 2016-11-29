#!/bin/bash
set -ex

for path in / /api/v2/articles /rss/articles/poa+vor/last-28-days/ /reports/paw/recent.xml; do
    [ $(curl --write-out %{http_code} --silent --output /dev/null https://$(hostname)$path) == 200 ]
done

for path in /admin /explorer; do
    [ $(curl --write-out %{http_code} --silent --output /dev/null https://$(hostname)$path) == 301 ]
done
