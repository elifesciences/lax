#!/bin/bash
set -e
sudo docker run -it -p 8001:8000 elifesciences/lax-develop /bin/bash -c 'cd /srv/lax/ && . venv/bin/activate && ./runserver.sh 0.0.0.0:8000'
echo '---'
echo "visit http://127.0.0.1:8001/"
