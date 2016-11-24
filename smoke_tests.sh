#!/bin/bash
set -ex

[ $(curl --write-out %{http_code} --silent --output /dev/null https://$(hostname)/) == 200 ]
[ $(curl --write-out %{http_code} --silent --output /dev/null https://$(hostname)/api/v2/articles) == 200 ]
