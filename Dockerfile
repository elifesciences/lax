FROM ubuntu:14.04
MAINTAINER Luke Skibinski <l.skibinski@elifesciences.org>

RUN DEBIAN_FRONTEND=noninteractive apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install \
    git wget vim python-pip screen \
    --no-install-recommends -y
RUN cd /srv/ && hg clone https://github.com/elifesciences/lax

WORKDIR /srv/lax
RUN virtualenv venv --python=`which python2`
RUN source venv/bin/activate
RUN pip install -r requirements.txt
RUN python src/manage.py syncdb --noinput
RUN python src/manage.py loaddata publisher/fixtures/admin-user.json
