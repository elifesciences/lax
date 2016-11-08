from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import date
from explorer import exporters, models
import logging
import botocore.session
import tinys3

LOG = logging.getLogger(__name__)

def _upload(key, data):
    credentials = botocore.session.get_session().get_credentials()
    access_key = credentials.access_key
    secret_key = credentials.secret_key
    conn = tinys3.Connection(access_key, secret_key, default_bucket=settings.EXPLORER_S3_BUCKET)
    return conn.upload(key, data)  # expects a file-like object

def snapshot_query(query_id):
    LOG.info("Starting snapshot for query %s..." % query_id)
    q = models.Query.objects.get(pk=query_id)
    exporter = exporters.get_exporter_class('csv')(q)
    k = 'query-%s.snap-%s.csv' % (q.id, date.today().strftime('%Y%m%d-%H:%M:%S'))
    LOG.info("Uploading snapshot for query %s as %s..." % (query_id, k))
    resp = _upload(k, exporter.get_file_output())
    LOG.info("Done uploading snapshot for query %s. URL: %s" % (query_id, resp.url))

class Command(BaseCommand):
    help = 'for snapshotting queries and uploading to s3 without celery'

    def add_arguments(self, parser):
        parser.add_argument('--query-id', dest='qid', type=int, required=False)

    def handle(self, *args, **options):
        qid = options['qid']

        qid_list = []
        if qid:
            qid_list = [qid]
        else:
            qid_list = models.Query.objects.all().values('id')

        map(snapshot_query, qid_list)
