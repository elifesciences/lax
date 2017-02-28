from publisher.utils import lmap
from et3.extract import lookup as p
import json
from reports import logic
from django.core.management.base import BaseCommand
import logging
from collections import ChainMap

LOG = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'status of data in this lax instance'

    def add_arguments(self, parser):
        parser.add_argument('paths', nargs='*')

    def pprint(self, x):
        print(json.dumps(x, indent=4))

    def handle(self, *args, **options):
        status = logic.status_report()
        paths = options['paths']

        def navigate(path):
            return {path: p(status, path)}

        # like (into {} [{...} {...} {...} {...}] in clojure
        self.pprint(dict(ChainMap(*lmap(navigate, paths) or [status])))
