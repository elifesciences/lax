"""
the `ingest` script is distinct from the `import` script. 

The import script does not obey business rules and merrily update published dates and so on without concern. It is good for bulk imports, development and once-off patching of article data.

The ingest script DOES obey business rules and will not publish things twice, 

"""

import sys, json, argparse
from django.core.management.base import BaseCommand
from publisher import ajson_ingestor
import logging

LOG = logging.getLogger(__name__)

IMPORT_TYPES = ['ingest', 'publish', 'ingest-publish']
INGEST, PUBLISH, BOTH = IMPORT_TYPES


class Command(BaseCommand):
    help = ''    
    def add_arguments(self, parser):
        # update articles that already exist?
        parser.add_argument('--force', action='store_true', default=False)

        parser.add_argument('--ingest', dest='action', action='store_const', const=INGEST)
        parser.add_argument('--publish', dest='action', action='store_const', const=PUBLISH)
        parser.add_argument('--ingest+publish', dest='action', action='store_const', const=BOTH)

        parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
        
        # version
        # msid

    def prn(self, *bits):
        self.stderr.write(''.join(map(str, bits)))
        self.stderr.write("\n")
        self.stderr.flush()
        
    def handle(self, *args, **options):
        force = options['force']
        action = options['action']
        data = options['infile']
        data = json.load(data)
        
        if not action:
            self.prn("no action specified!")
            exit(1)
        
        #self.prn('force?',force)
        #self.prn('data?',data)
        
        choices = {
            INGEST: ajson_ingestor.ingest,
            PUBLISH: ajson_ingestor.publish,
            BOTH: ajson_ingestor.ingest_publish,
        }

        try:
            choices[action](data, force)
        except ajson_ingestor.StateError as err:
            print err.message
            exit(1)
