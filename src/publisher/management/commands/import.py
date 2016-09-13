import os, glob, pprint
from django.core.management.base import BaseCommand
from django.db import transaction
from publisher import eif_ingestor, logic, ejp_ingestor
from functools import partial
import logging

LOG = logging.getLogger(__name__)

IMPORT_TYPES = ['eif', 'ejp', 'ajson', 'patch']
EIF, EJP, AJSON, PATCH = IMPORT_TYPES

def resolve_path(p):
    p = os.path.abspath(p)
    if os.path.isdir(p):
        return glob.glob("%s/*.json" % p.rstrip('/'))
    return [p]

def ingest(fn, journal, create, update, path_list):
    "wrapper around the import function with friendlier handling of problems"
    def _(path):
        try:
            results = fn(journal, path, create=create, update=update)
            LOG.debug("results of ingest", extra={'results': results})
            return True
        except KeyboardInterrupt:
            raise
        except:
            LOG.exception("failed to import article")
            return False
    try:
        map(_, path_list)
    except KeyboardInterrupt:
        print 'caught interrupt'
        exit(1)

class Command(BaseCommand):
    help = '''
    The `import` command imports article data from different sources, default to an EIF source.

    This command supercedes the `import_article` and `import_ejp_article` commands.

    Lax requires all data sources to be JSON encoded. 

    To specify the type of import to be performed, use the `--import-type` parameter.

    A single JSON file or a directory of JSON may be passed in as the `--path` paramater. 
    Directories of files will have their contents expanded and only JSON files will be used.

    To only create articles and never update an article, use the `--no-update` parameter.

    To only update articles and never create articles, use the `--no-create` parameter.

    To neither create nor update (a dry run), use both `--no-create` and `--no-update` parameters.'''
    
    def add_arguments(self, parser):
        # where am I to look?
        parser.add_argument('path', type=str)
        # create articles that don't exist?
        parser.add_argument('--no-create', action='store_false', default=True)
        # update articles that already exist?
        parser.add_argument('--no-update', action='store_false', default=True)
        # indicate the type of import we should be doing
        parser.add_argument('--import-type', type=str, choices=IMPORT_TYPES)
        # don't prompt, don't pretty-print anything, just do it.
        parser.add_argument('--just-do-it', action='store_true', default=False)
        # do the import within a transaction - default. makes sqlite fly
        parser.add_argument('--no-atomic', action='store_false', default=True)
    
    def handle(self, *args, **options):
        path = options['path']
        create_articles = options['no_create']
        update_articles = options['no_update']
        import_type = options['import_type']
        atomic = options['no_atomic']

        path_list = resolve_path(path)

        if not options['just_do_it']:
            try:
                pprint.pprint(path_list)
                print
                print import_type.upper(),'import of',len(path_list),'files'
                print 'create?',create_articles
                print 'update?',update_articles
                print
                raw_input('continue? (ctrl-c to exit)')
            except KeyboardInterrupt:
                print
                exit(0)
        
        choices = {
            EIF: eif_ingestor.import_article_from_json_path,
            EJP: ejp_ingestor.import_article_list_from_json_path,
            PATCH: eif_ingestor.patch_handler,
            AJSON: None
        }
        fn = partial(ingest, choices[import_type], logic.journal(), create_articles, update_articles, path_list)
        if atomic:
            with transaction.atomic():
                return fn()
        return fn()
