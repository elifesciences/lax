#!/bin/bash
set -ex

for path in / /api/v2/articles; do
    [ $(curl --write-out %{http_code} --silent --output /dev/null https://$(hostname)$path) == 200 ]
done

for path in /admin /explorer; do
    [ $(curl --write-out %{http_code} --silent --output /dev/null https://$(hostname)$path) == 301 ]
done

# api-raml version must be identical for lax and bot-lax-adaptor
diff /opt/bot-lax-adaptor/api-raml.sha1 api-raml.sha1
