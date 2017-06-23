from django.core.management.base import BaseCommand
import logging
from publisher import models, fragment_logic, utils

LOG = logging.getLogger(__name__)

# all-article-versions-as-csv
def avl2csv(stdout, stderr):
    import csv
    rs = models.ArticleVersion.objects \
        .select_related('article') \
        .defer('article_json_v1', 'article_json_v1_snippet') \
        .order_by('article__manuscript_id', 'version') \
        .all()

    def mkrow(av):
        msid = utils.pad_msid(av.article.manuscript_id)
        version = av.version
        loc = fragment_logic.location(av)
        if ',' in loc:
            # bad data that may screw up consumers
            LOG.warn("bad data! location for %s, version %s contains a comma: %s", msid, version, loc)
        return [msid, version, loc]

    try:
        writer = csv.writer(stdout, lineterminator="\n")
        [writer.writerow(mkrow(row)) for row in rs]
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
        exit(ret)

    def handle(self, *args, **options):
        cmd = options['report']
        opts = {
            'all-article-versions-as-csv': avl2csv
        }
        try:
            if cmd not in opts:
                self.die("report not found")

            opts[cmd](self.stdout, self.stderr)
            exit(0)

        finally:
            self.stdout.flush()
            self.stderr.flush()
