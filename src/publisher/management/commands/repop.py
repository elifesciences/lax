import os
from pprint import pprint
from django.core.management.base import BaseCommand
from django.core.management import call_command
import boto3

import logging
logger = logging.getLogger(__name__)

def mkstruct(o):
    keys = ['key', 'last_modified']
    struct = dict(map(lambda attr: (attr, getattr(o, attr)), keys))
    struct.update(dict(zip(['aid', 'uuid', 'fname'], struct['key'].split('/'))))
    struct['last_modified'] = struct['last_modified'].strftime('%Y-%m-%d-%H-%M-%S')
    #struct['obj'] = o
    return struct

class Command(BaseCommand):
    help = '''Repopulates the lax database using the contents of the elife-publishing-eif bucket. If article has multiple attempts, use the most recent attempt. Matching articles will be downloaded and imported using the `import_articles` command'''
    
    def handle(self, *args, **options):
        s3 = boto3.resource('s3')
        bucket = s3.Bucket('elife-publishing-eif')
        q = bucket.objects.all()
        #q = bucket.objects.limit(count=10)
        # turn those objects into something we can deal with
        dataset = map(mkstruct, q)
        # order everything by when they were modified, from earliest to oldest
        dataset = sorted(dataset, key=lambda x: x['last_modified'])
        # key by fname so more recent runs of the same file override previous runs
        struct_map = {}
        run_replacements = {}
        for struct in dataset:
            key = struct['fname']
            if struct_map.has_key(key):
                old_run = struct_map[key]['last_modified']
                new_run = struct['last_modified']
                print '%s: replacing run %s with %s' % (key, old_run, new_run)
                if not run_replacements.has_key(key):
                    run_replacements[key] = []
                run_replacements[key].append((old_run, new_run))
            struct_map[key] = struct
        # download everything
        os.system('mkdir -p .repop')
        def download(s):
            path = '.repop/%s' % s['fname']
            if os.path.exists(path):
                print 'file exists, NOT downloading',s['key']
            else:
                print 'downloading',s['key']
                bucket.download_file(s['key'], path)
            return key
        map(download, dataset)

        cmd = "import_article path .repop/ --no-update"
        call_command(*cmd.split())
