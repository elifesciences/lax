# Lax

An effort to provide a flexible, mostly-structured, data store for articles.

A publisher has one or many journals, each journal has many articles.

Each article is uniquely identified by it's DOI + version number.

Each article has zero or many attributes in a simple `key=val` table that 
supplements the version-insensitive article data.

## The 'Publisher' app

The core application on which other apps may be dependant.

It models the basic relationships between entities and captures events occurring
against Articles.

## Installation

    $ git clone https://github.com/elifesciences/lax
    $ ./lax/install.sh

## Updating

    $ ./install.sh

## Credentials

The admin username and password are "admin" and "admin. This user can also be 
created with:

    $ ./src/manage.py loaddata src/publisher/fixtures/admin-user.json

If you are running the Dockerized version of Lax this admin user already exists.

## Running

    $ python src/manage.py runserver
    $ firefox http://127.0.0.1:8000/admin
    
## Loading Article JSON

    $ ./load-json.sh /path/to/json/dir/
    
or, via http:
    
    $ curl -vX POST http://127.0.0.1:8000/import-article/ \
      --data @article.json \
      --header "Content-Type: application/json"

## Adding Article Attributes

    $ curl -vX POST http://127.0.0.1:8000/add-attribute-to-article/<doi>/<version>/ \
      --data {"key": "Date Published", "val": "1997-08-29 06:14:00+UTC"} \
      --header "Content-Type: application/json"

## Testing

    $ ./test.sh
    
