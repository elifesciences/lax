import os
from django.core.management.base import BaseCommand
import boto3

import logging
logger = logging.getLogger(__name__)

def pub_eif_struct(o):
    keys = ['key', 'last_modified']
    struct = dict(map(lambda attr: (attr, getattr(o, attr)), keys))
    # fname ll: elife-00003-v1.json
    struct.update(dict(zip(['aid', 'uuid', 'fname'], struct['key'].split('/'))))
    struct['last_modified'] = struct['last_modified'].strftime('%Y-%m-%d-%H-%M-%S')
    #struct['obj'] = o
    return struct

def pub_archive_struct(o):
    # key ll: 'elife-12916-poa-v1-20151229000000.zip'
    aid, status, ver, rest = o.key.rsplit('-', 3)
    # will match the key used from elife-publishing-eif
    artificial_key = "%s-%s.json" % (aid, ver) # ll: elife-12916-v1.json
    return artificial_key

def bucket_listing(bucket, limit=None):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket)
    if not limit:
        return bucket, bucket.objects.all()
    return bucket, bucket.objects.limit(count=limit)

class Command(BaseCommand):
    help = '''Repopulates the lax database using the contents of the elife-publishing-eif bucket. If article has multiple attempts, use the most recent attempt. Matching PUBLISHED articles will be downloaded and imported using the `import_articles` command. Published status is determined by an entry in the elife-publishing-archive bucket'''

    def handle(self, *args, **options):
        pub_eif_bucket, dataset = bucket_listing('elife-publishing-eif')  # , limit=10)
        # turn those objects into something we can deal with
        dataset = map(pub_eif_struct, dataset)
        # order everything by when they were modified, from earliest to oldest
        dataset = sorted(dataset, key=lambda x: x['last_modified'])
        # key by fname so more recent runs of the same file override previous runs
        struct_map = {}
        run_replacements = {}
        for struct in dataset:
            key = struct['fname']
            if key in struct_map:
                old_run = struct_map[key]['last_modified']
                new_run = struct['last_modified']
                print '%s: replacing run %s with %s' % (key, old_run, new_run)
                if key not in run_replacements:
                    run_replacements[key] = []
                run_replacements[key].append((old_run, new_run))
            struct_map[key] = struct

        pub_archive_bucket, published_dataset = bucket_listing('elife-publishing-archive')  # , limit=10)
        idx = set(map(pub_archive_struct, published_dataset))

        # download everything
        os.system('mkdir -p .repop')

        def download(s):
            path = '.repop/%s' % s['fname']
            if s['fname'] not in idx:
                print 'file not published yet, NOT downloading', s['key']
            elif os.path.exists(path):
                # print 'file exists, NOT downloading',s['key']
                pass
            else:
                print 'downloading', s['key']
                pub_eif_bucket.download_file(s['key'], path)
            return key

        map(download, sorted(struct_map.values()))
