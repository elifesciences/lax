# Lax

An effort by [eLife Sciences](http://elifesciences.org) to provide a flexible, mostly-structured, data store 
for articles.

API documentation can be found here:

* [Swagger](https://lax.elifesciences.org/api/docs/) (or your [local version](/api/docs/))
* [code](https://github.com/elifesciences/lax/blob/master/src/publisher/api.py)

## Installation

[code](https://github.com/elifesciences/lax/blob/develop/install.sh)  

    $ git clone https://github.com/elifesciences/lax
    $ cd lax
    $ ./install.sh

## Updating

[code](https://github.com/elifesciences/lax/blob/develop/install.sh)  

    $ ./install.sh

## Testing 

[code](https://github.com/elifesciences/lax/blob/develop/src/publisher/tests/)  

    $ ./test.sh

## Running

[code](https://github.com/elifesciences/lax/blob/develop/runserver.sh)

    $ ./runserver.sh
    $ firefox http://127.0.0.1:8000/admin

## Loading Article JSON

eLife uses a JSON format called [EIF](https://github.com/elifesciences/elife-eif-schema) 
(eLife Ingestor Format) that was designed to convert JATS XML into something 
malleable for the website and other downstream projects (like Lax).

The eLife EIF JSON can be imported with:

    $ ./load-elife-json.sh

This will clone the EIF JSON and load it sequentially into Lax.

or, via http:
    
    $ curl -vX POST http://127.0.0.1:8000/api/v1/article/create-update/ \
      --data @eif-article-file.json \
      --header "Content-Type: application/json"


## Data model

[code](https://github.com/elifesciences/lax/blob/master/src/publisher/models.py)

A publisher has one or many journals, each journal has many articles.

Each article is uniquely identified by it's DOI. The DOI doesn't have to be 
registered with Crossref.

Each article consists of a set of [known attributes](https://github.com/elifesciences/lax/blob/develop/src/publisher/models.py#L24) that are stored together in the database.

Each article also has zero or many attributes in a simple `key=val` table that 
supplements the normalised article data. This allows for collection of ad-hoc 
article data. These attributes and their values may be migrated into the 
`article` database table at a later point.

## The 'Publisher' app

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

