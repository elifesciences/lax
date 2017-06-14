from django.core.management.base import BaseCommand
import logging
from publisher import models, fragment_logic, utils

LOG = logging.getLogger(__name__)

def avl2csv():

    rs = models.ArticleVersion.objects \
        .select_related('article') \
        .defer('article_json_v1', 'article_json_v1_snippet') \
        .order_by('article__manuscript_id', 'version') \
        .all()

    def mkrow(av):
        return [
            utils.pad_msid(av.article.manuscript_id),
            av.version,
            fragment_logic.location(av)
        ]

    def writerow(row):
        print(','.join(map(str, row)))

    try:
        [writerow(mkrow(row)) for row in rs]
    except KeyboardInterrupt:
        exit(1)

#
#
#

class Command(BaseCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument('report')

    def die(self, msg, ret=1):
        self.stderr.write(msg)
        self.stderr.flush()
        exit(ret)

    def handle(self, *args, **options):
        cmd = options['report']
        opts = {
            'all-article-versions-as-csv': avl2csv
        }
        if cmd not in opts:
            return self.die("report not found")

        opts[cmd]()
        exit(0)
