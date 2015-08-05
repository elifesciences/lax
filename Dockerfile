FROM ubuntu:14.04
MAINTAINER Luke Skibinski <l.skibinski@elifesciences.org>
RUN rm /bin/sh && ln -s /bin/bash /bin/sh
RUN DEBIAN_FRONTEND=noninteractive LANG=C apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install \
    git wget vim python-pip screen \
    --no-install-recommends -y
RUN pip install virtualenv
RUN cd /srv/ && git clone https://github.com/elifesciences/lax -b develop

RUN cd /srv/lax/ && ./install.sh
WORKDIR /srv/lax/src
RUN source ../venv/bin/activate && echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin')" | ./manage.py shell
RUN echo "done!"
