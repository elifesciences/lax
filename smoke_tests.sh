#!/bin/bash
set -ex

wait_for_port 80

num_attempts=3
retry_delay=5 # seconds

request () {
    host=$(hostname)
    path="$1"
    expected="$2"
    actual=$(curl --retry $num_attempts --retry-delay $retry_delay --write-out "%{http_code}" --silent --output /dev/null "https://$host$path")
    test "$expected" = "$actual"
}

for path in / /api/v2/articles; do
    request "$path" 200
done

for path in /admin /explorer; do
    request "$path" 301
done


# api-raml version must be identical for lax and bot-lax-adaptor
diff /opt/bot-lax-adaptor/api-raml.sha1 api-raml.sha1
