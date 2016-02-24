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

* [https://lax.elifesciences.org/api/v1/api/v1/article/10.7554/eLife.09560/](https://lax.elifesciences.org/api/v1/api/v1/article/10.7554/eLife.09560/)

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

## updating

[code](https://github.com/elifesciences/lax/blob/master/install.sh)  

    ./install.sh

## testing 

[code](https://github.com/elifesciences/lax/blob/master/src/publisher/tests/)  

    ./test.sh

## running

[code](https://github.com/elifesciences/lax/blob/master/runserver.sh)

    ./runserver.sh
    firefox http://127.0.0.1:8000/api/docs/

## loading article JSON

eLife uses a JSON format called [EIF](https://github.com/elifesciences/elife-eif-schema) 
(eLife Ingestor Format) that was designed to convert JATS XML into something 
malleable for the website and other downstream projects (like Lax).

The eLife EIF JSON can be imported with:

    ./load-elife-json.sh

This will clone the EIF JSON and load it sequentially into Lax.

or, via http:
    
    curl -vX POST http://127.0.0.1:8000/api/v1/article/create-update/ \
      --data @eif-article-file.json \
      --header "Content-Type: application/json"


## data model

[code](https://github.com/elifesciences/lax/blob/master/src/publisher/models.py)

A publisher has one or many journals, each journal has many articles.

Each article is uniquely identified by it's DOI. The DOI doesn't have to be 
registered with Crossref.

Each article consists of a set of [known attributes](https://github.com/elifesciences/lax/blob/master/src/publisher/models.py#L24) that are stored together in the database.

Each article also has zero or many attributes in a simple `key=val` table that 
supplements the normalised article data. This allows for collection of ad-hoc 
article data. These attributes and their values may be migrated into the 
`article` database table at a later point.

## the 'Publisher' app

[code](https://github.com/elifesciences/lax/blob/master/src/publisher/)

The core application on which other apps may be dependant.

It models the basic relationships between entities and captures events occurring
against Articles.

Both the `Article` and `ArticleAttribute` models in the Publisher app keep a 
record of data that is changed. If an article is updated, it's previous version 
is kept and can be queried if you want insight into it's history.

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

