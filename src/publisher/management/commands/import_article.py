import os, glob, pprint
from django.core.management.base import BaseCommand
from publisher import ingestor, logic, utils
from functools import partial

import logging
logger = logging.getLogger(__name__)

def resolve_path(p):
    print 'resolving',p
    p = os.path.abspath(p)
    if os.path.isdir(p):
        return glob.glob("%s/*.json" % p.rstrip('/'))
    return p

def import_fn(create, update, path):
    "wrapper around the import function with friendlier handling of problems"
    print 'importing',path,'...'
    try:
        ingestor.import_article_from_json_path(logic.journal(), path, create=create, update=update)
        success = True
    except KeyboardInterrupt:
        raise
    except AssertionError, ae:
        print ae
        success = True
    except:
        logger.exception("failed to import article")
        success = False
    return path, success

class Command(BaseCommand):
    help = 'Imports one or many article JSON files or directories of files'
    
    def add_arguments(self, parser):
        # where am I to look?
        parser.add_argument('paths', nargs='+', type=str)
        # create articles that don't exist?
        parser.add_argument('--no-create', action='store_false', default=True)
        # update articles that already exist?
        parser.add_argument('--no-update', action='store_false', default=True)
    
    def handle(self, *args, **options):
        paths = options['paths']
        create_articles = options['no_create']
        update_articles = options['no_update']
        
        path_list = list(set(utils.flatten(map(resolve_path, paths))))
        if not path_list:
            print 'no files to process, exiting'
            exit(0)

        try:
            pprint.pprint(path_list)
            print 'create?',create_articles
            print 'update?',update_articles
            
            print 'importing %s files:' % len(path_list)
            raw_input('continue? (ctrl-c to exit)')
        except KeyboardInterrupt:
            print
            exit(0)

        try:
            if not create_articles and not update_articles:
                print 'cannot create or update, stopping here.'
                exit(0)

            fn = partial(import_fn, create_articles, update_articles)
            results = map(fn, path_list)
            pprint.pprint(results)

        except KeyboardInterrupt:
            print
            exit(1)
