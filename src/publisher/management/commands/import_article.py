import os, glob, pprint
from core import utils as core_utils
from django.core.management.base import BaseCommand, CommandError
from publisher import models, json_import as ingestor, logic

import logging
logger = logging.getLogger(__name__)

def resolve_path(p):
    print 'resolving',p
    p = os.path.abspath(p)
    if os.path.isdir(p):
        return glob.glob("%s/*.json" % p.rstrip('/'))
    return p

class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('paths', nargs='+', type=str)
    
    def handle(self, *args, **kwargs):
        paths = kwargs['paths']
        path_list = list(set(core_utils.flatten(map(resolve_path, paths))))
        if not path_list:
            print 'no files to process, exiting'
            exit(0)

        try:
            pprint.pprint(path_list)
            print 'importing %s files:' % len(path_list)
            raw_input('continue? (ctrl-c to exit)')
        except KeyboardInterrupt:
            print
            exit(0)

        def _import(path):
            print 'importing',path,'...'
            try:
                ingestor.import_article(journal, path)
                success = True
            except Exception, e:
                logger.exception("failed to import article")
                success = False
            return path, success

        journal = logic.journal()
        results = map(_import, path_list)
        pprint.pprint(results)
