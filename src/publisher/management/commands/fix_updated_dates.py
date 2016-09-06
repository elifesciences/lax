import os, json
from pprint import pprint
from publisher import eif_ingestor
from django.core.management.base import BaseCommand
from django.core.management import call_command

import logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = """'Patches' articles using json corresponding to model attributes """
    
    def handle(self, *args, **options):
        fname = './updated-dates/output.json'
        data = map(json.loads, open(fname, 'r').readlines())
        
        def mkpatch(d):
            v = {}
            for ver in d['versions']:
                v[int(ver['version'])] = ver
                ver['datetime_published'] = ver['pub-date']
                del ver['pub-date']
                del ver['version']
            d['versions'] = v
            return d
        map(eif_ingestor.patch, map(mkpatch, data))
