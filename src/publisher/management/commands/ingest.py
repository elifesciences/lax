"""
the `ingest` script is distinct from the `import` script. 

The import script does not obey business rules and merrily update published dates and so on without concern. It is good for bulk imports, development and once-off patching of article data.

The ingest script DOES obey business rules and will not publish things twice, 

"""

import sys, json, argparse
from django.core.management.base import BaseCommand
from publisher import ajson_ingestor
from publisher.ajson_ingestor import StateError
import logging

LOG = logging.getLogger(__name__)

INVALID = 'invalid'
IMPORT_TYPES = ['ingest', 'publish', 'ingest-publish']
INGEST, PUBLISH, BOTH = IMPORT_TYPES
INGESTED, PUBLISHED = 'ingested', 'published'

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

    def write(self, out=None):
        if not isinstance(out, basestring):
            out = json.dumps(out)
        self.stdout.write(out)
        self.stdout.flush()

    def error(self, errtype, message):
        return self.write({
            'status': errtype,
            'message': message
        })

    def success(self, action, jaav):
        status = INGESTED if action == INGEST else PUBLISHED
        j, a, av = jaav
        return self.write({
            'status': status,
            'id': a.manuscript_id,
            'datetime': av.datetime_published
        })

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        action = options['action']
        data = options['infile']

        if not action:
            self.error(INVALID, "no action specified. I need either a 'ingest', 'publish' or 'ingest+publish' action")
            sys.exit(1)

        try:
            data = json.load(data)
        except ValueError as err:
            self.error(INVALID, "could decode the json you gave me: %s" % err.message)
            sys.exit(1)

        choices = {
            INGEST: ajson_ingestor.ingest,
            PUBLISH: ajson_ingestor.publish,
            BOTH: ajson_ingestor.ingest_publish,
        }

        try:
            jaav = choices[action](data, dry_run, force)
            self.success(action, jaav)

        except StateError as err:
            msg = "failed to call action %r: %s" % (action, err.message)
            self.error(INVALID, msg)
            sys.exit(1)

        sys.exit(0)
