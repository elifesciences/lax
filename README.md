# Lax
 
Lax is a data storage application for articles at eLife Sciences.

This project uses the [Python programming language](https://www.python.org/), 
the [Django web framework](https://www.djangoproject.com/) and a
[relational database](https://en.wikipedia.org/wiki/Relational_database_management_system).

## API

Documentation can be found here:

* [API GUI](https://api.elifesciences.org/documentation/#articles)
* [code](https://github.com/elifesciences/lax/blob/master/src/publisher/api.py)

For example, the [Homo Naledi](https://elifesciences.org/articles/09560) article:

* [https://lax.elifesciences.org/api/v2/articles/09560](https://lax.elifesciences.org/api/v2/articles/09560)

## install

[code](https://github.com/elifesciences/lax/blob/master/install.sh)  

    git clone https://github.com/elifesciences/lax
    cd lax
    ./install.sh

PostgreSQL is used in production which depends on psycopg2 and your distribution's 'libpq' library.

## update

[code](https://github.com/elifesciences/lax/blob/master/install.sh)  

    ./install.sh

## test

[code](https://github.com/elifesciences/lax/blob/master/src/publisher/tests/)  

    ./test.sh

## run (development)

[code](https://github.com/elifesciences/lax/blob/master/runserver.sh)

    ./manage.sh runserver
    firefox http://127.0.0.1:8000/api/docs/

## data model

[code](https://github.com/elifesciences/lax/blob/master/src/publisher/models.py)

A *publisher* has one or many *journals*, each journal has many *articles* and each each article has many *versions*.

Each article is uniquely identified by its 'manuscript id', a simple integer.

Each article version contains the final article-json (derived from the article's JATS xml), the date and time it was 
published, updated, etc.

Each article also has one or many *article fragments*. Article fragments are merged to become the final article-json.
There is one main fragment - the 'xml to json' fragment - and occasionally smaller fragments added by services that 
produce article content outside of the typical article production workflow.

Each article may have many *events* associated with it, such as when it was received, reviewed, decisions made, etc.

Each article version may be *related* to other *articles* (not article *versions*) internally within Lax as well 
externally via a URL.

## loading article-json

Lax supports an eLife-specific JSON representation of JATS XML called 'article-json'.

[article-json](https://github.com/elifesciences/api-raml/blob/develop/dist/model/article-vor.v1.json) is part of elife's 
overall API definition and used extensively.

article-json files can be imported into Lax with:

[code](https://github.com/elifesciences/lax/blob/master/src/publisher/management/commands/ingest.py)

    ./manage.sh ingest /path/to/article.json
    
See also [bot-lax-adaptor](https://github.com/elifesciences/bot-lax-adaptor) for converting JATs XML to article-json and
bulk loading content using 'backfills'.

## Copyright & Licence

Copyright 2021 eLife Sciences. Licensed under the [GPLv3](LICENCE.txt)

