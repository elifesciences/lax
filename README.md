# Lax
 
An effort by [eLife Sciences](http://elifesciences.org) to provide a flexible, 
mostly-structured, data store for articles.

This project uses the [Python programming language](https://www.python.org/),
the [Django web framework](https://www.djangoproject.com/) and a
[relational database](https://en.wikipedia.org/wiki/Relational_database_management_system).

[Github repo](https://github.com/elifesciences/lax/).

## API

Documentation can be found here:

* [code](https://github.com/elifesciences/lax/blob/master/src/publisher/api.py)
* [Swagger](https://lax.elifesciences.org/api/docs/) (or your [local version](/api/docs/))

For example, the [Homo Naledi](http://elifesciences.org/content/4/e09560) article:

* [https://lax.elifesciences.org/api/v2/articles/09560](https://lax.elifesciences.org/api/v2/articles/09560)

## RSS

RSS feeds are available here:

* [code](https://github.com/elifesciences/lax/blob/master/src/publisher/rss.py)
* [articles published in the last day](https://lax.elifesciences.org/rss/articles/poa+vor/last-1-days/) \[[POA](https://lax.elifesciences.org/rss/articles/poa/last-1-days/)\] \[[VOR](https://lax.elifesciences.org/rss/articles/vor/last-1-days/)\], or [last week](https://lax.elifesciences.org/rss/articles/poa+vor/last-7-days/) \[[POA](https://lax.elifesciences.org/rss/articles/poa/last-7-days/)\] \[[VOR](https://lax.elifesciences.org/rss/articles/vor/last-7-days/)\]

The URLs look like:

    https://lax.elifesciences.org/rss/articles/<status[+status]>/last-<n>-days/

For example, if you wanted all articles published in the last month:

    https://lax.elifesciences.org/rss/articles/poa+vor/last-28-days/

## installation

[code](https://github.com/elifesciences/lax/blob/master/install.sh)  

    git clone https://github.com/elifesciences/lax
    cd lax
    ./install.sh

Postgresql is used in production so there is a dependency on psycopg2 which 
requires your distribution's 'libpq' library to be installed. On Arch Linux, 
this is 'libpqxx', on Ubuntu this is 'libpq-dev'.

## updating

[code](https://github.com/elifesciences/lax/blob/master/install.sh)  

    ./install.sh

## testing 

[code](https://github.com/elifesciences/lax/blob/master/src/publisher/tests/)  

    ./test.sh

## running

[code](https://github.com/elifesciences/lax/blob/master/runserver.sh)

    ./manage.sh runserver
    firefox http://127.0.0.1:8000/api/docs/

## data model

[code](https://github.com/elifesciences/lax/blob/master/src/publisher/models.py)

A publisher has one or many journals, each journal has many articles.

Each article is uniquely identified by it's 'manuscript id', a simple integer.

Each article may have many versions. Each article version contains the 
article-json (derived from the article's JATS xml), the date and time it was
published, etc.

## loading article JSON

Lax has support for two internal (to eLife) types of article json: EIF and 
'article-json'. 

[EIF](https://github.com/elifesciences/elife-eif-schema) was a loosely 
structured format that was extremely convenient for sharing just the important 
bulk of article data between the elife-bot, lax, and the Drupal journal website.

This format is deprecated and support will eventually be removed.

The other format is [article-json](https://github.com/elifesciences/api-raml/blob/develop/dist/model/article-vor.v1.json), 
defined as part of elife's API definition effort and used extensively in our 
new infrastructure.

These article-json files can be imported into Lax with:

[code](https://github.com/elifesciences/lax/blob/master/src/publisher/management/commands/ingest.py)

    ./manage.sh ingest /path/to/article.json
    
See the [bot-lax-adaptor](https://github.com/elifesciences/bot-lax-adaptor) for
converting JATs XML to article-json.

## Copyright & Licence

Copyright 2016 eLife Sciences. Licensed under the [GPLv3](LICENCE.txt)

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

