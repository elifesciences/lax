import os, glob, pprint
from django.core.management.base import BaseCommand
from publisher import ingestor, logic, utils, ejp_ingestor
from functools import partial

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = ''
    
    def add_arguments(self, parser):
        # where am I to look?
        parser.add_argument('path', type=str)
        # create articles that don't exist?
        parser.add_argument('--no-create', action='store_false', default=True)
        # update articles that already exist?
        parser.add_argument('--no-update', action='store_false', default=True)
    
    def handle(self, *args, **options):
        path = options['path']
        create_articles = options['no_create']
        update_articles = options['no_update']

        path = os.path.abspath(path)
        
        print 'path',path
        print 'create?',create_articles
        print 'update?',update_articles
        
        ejp_ingestor.import_article_list_from_json_path(logic.journal(), path, create_articles, update_articles)
