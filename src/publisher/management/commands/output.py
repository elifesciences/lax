# not working, unused
'''
from publisher import logic
from django.core.management.base import BaseCommand
from publisher import utils
import logging

LOG = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'for exporting views of data from lax'

    def add_arguments(self, parser):
        #parser.add_argument('--id', dest='msid', type=int, required=True)
        #parser.add_argument('--version',  dest='version', type=int, required=True)
        parser.add_argument('--type', choices=['article-version-history', 'article-json'])
        pass

    def write(self, out=None):
        if not isinstance(out, str):
            out = utils.json_dumps(out) # encodes datetime objects
        self.stdout.write(out)
        self.stdout.flush()

    def handle(self, *args, **options):
        output_type = options['type']

        output_type_map = {
            'article-version-history': logic.bulk_article_version_history
        }

        for row in output_type_map[output_type]():
            print(utils.json_dumps(row))
'''
