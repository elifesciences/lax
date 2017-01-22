import sys, json
from functools import partial
from .modcommand import ModCommand
from publisher.utils import boolkey
from publisher.fragment_logic import revalidate_specific_article_version, revalidate_all_versions_of_article, revalidate_all_article_versions, revalidate_report
import logging

LOG = logging.getLogger('')
LOG.setLevel(logging.CRITICAL)

class Command(ModCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument('--id', dest='msid', type=int)
        parser.add_argument('--version', dest='version', type=int)
        parser.add_argument('--dry-run', action='store_true', default=False)

        self.parser = parser

    def invalid_args(self, message):
        self.parser.error(message)
        sys.exit(1)

    def handle(self, *args, **options):
        msid, version = options.get('msid'), options.get('version')
        matrix = {
            # msid?, version?
            (True, True): partial(revalidate_specific_article_version, msid, version),
            (True, False): partial(revalidate_all_versions_of_article, msid),
            (False, False): revalidate_all_article_versions,

            (False, True): partial(self.invalid_args, "an '--id' must be provided if a '--version' is supplied")
        }
        results = matrix[boolkey(msid, version)](dry_run=options['dry_run'])
        self.stdout.write(json.dumps(revalidate_report(results), indent=4))
        sys.exit(0)
