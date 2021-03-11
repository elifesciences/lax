#!/bin/bash
set -ex

num_attempts=3
retry_delay=5 # seconds

for path in / /api/v2/articles; do
    [ $(curl --retry $num_attempts --retry-delay $retry_delay --write-out %{http_code} --silent --output /dev/null https://$(hostname)$path) == 200 ]
done

for path in /admin /explorer; do
    [ $(curl --retry $num_attempts --retry-delay $retry_delay --write-out %{http_code} --silent --output /dev/null https://$(hostname)$path) == 301 ]
done


# api-raml version must be identical for lax and bot-lax-adaptor
diff /opt/bot-lax-adaptor/api-raml.sha1 api-raml.sha1
