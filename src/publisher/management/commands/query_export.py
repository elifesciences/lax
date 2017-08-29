import io
import sys
from publisher.utils import subdict, lmap
from functools import partial
from slugify import slugify
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import date
from explorer import exporters, models
import logging
import boto3

LOG = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'for snapshotting queries and uploading to s3 without celery'

    def add_arguments(self, parser):
        parser.add_argument('--query-id', dest='qid', type=int, required=False)
        parser.add_argument('--skip-upload', action='store_false', dest='upload')

    def _upload(self, key, data):
        # assume boto can find our credentials
        s3 = boto3.resource('s3')
        # django-sql-explorer on master branch has fixed this issue but it's still present
        # in 1.0. `get_file_output()` is casting to a str before returning
        data = io.BytesIO(data.getvalue().encode())
        s3.Bucket(settings.EXPLORER_S3_BUCKET).put_object(Key=key, Body=data)

    def snapshot_query(self, query_id, upload=True):
        q = models.Query.objects.get(pk=query_id)
        exporter = exporters.get_exporter_class('csv')(q)
        safe_title = slugify(q.title)

        # ll: query1--dummy-query.csv
        daily_fname = 'query%s--%s.csv' % (q.id, safe_title) 
        
        # ll: query1--dummy-query--2016-01-31-23-59-59.csv        
        timestamped_fname = 'query%s--%s--%s.csv' % (q.id, safe_title, date.today().strftime('%Y-%m-%d-%H-%M-%S'))

        res = exporter.query.execute_query_only()
        data = exporter._get_output(res)
        
        for fname in [daily_fname, timestamped_fname]:
            if upload and settings.EXPLORER_S3_BUCKET:
                LOG.info("uploading snapshot: %s", fname)
                self._upload(fname, data)
                #self._upload(fname, exporter.get_file_output())
                LOG.info("completed upload of snapshot: %s", fname)
                self.echo('%s uploaded' % fname)
            else:
                LOG.warn("the bucket to upload query result %r hasn't been defined in your app.cfg file. skipping upload" % fname)

        self.echo(daily_fname)

    def echo(self, x):
        self.stdout.write(str(x))
        self.stdout.flush()

    def handle(self, *args, **options):
        try:
            qid = options['qid']
            qid_list = []
            if qid:
                qid_list = [qid]
            else:
                qid_list = models.Query.objects.all().values_list('id', flat=True)

            if not qid_list:
                LOG.info("no query objects found, nothing to upload")
            else:
                fnargs = subdict(options, ['upload'])
                lmap(partial(self.snapshot_query, **fnargs), qid_list)

        except Exception as err:
            LOG.exception(err)
            self.echo(str(err))
            sys.exit(1)

        sys.exit(0)
