# unused code
'''
import sys
from django.core.management.base import BaseCommand
from publisher import aws_events, models
import logging

LOG = logging.getLogger(__name__)

class Command(BaseCommand):
    help = ''

    def add_arguments(self, parser):
        # update articles that already exist?
        parser.add_argument('--env', required=True, choices=['ci', 'end2end', 'prod'])
        parser.add_argument('--msid', type=int)
        parser.add_argument('--listen', action='store_true', default=False)

    def handle(self, *args, **options):
        env = options['env']

        if options['listen']:
            aws_events.listen(env)
        else:
            msid = options['msid']
            if not msid:
                # pull a random record
                msid = models.Article.objects.all().order_by('?')[0].manuscript_id
            art = models.Article.objects.get(manuscript_id=msid)
            # notify bus about this article
            aws_events.notify(art, env=env)

        sys.exit(0)
'''
