from publisher import models, fragment_logic
from django.core.management.base import BaseCommand
import sys
import logging
from django.db import transaction

LOG = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "calculates the hash for the stored article-json. completes in less than 2 mins"
    )

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # poa then vor articles. expect slowdown at about 36%
                q = models.ArticleVersion.objects.all().order_by("status")
                num = q.count()
                # `.iterator()` to use server-side cursor and avoid thrashing memory
                # https://docs.djangoproject.com/en/3.2/ref/models/querysets/#iterator
                for i, av in enumerate(q.iterator()):
                    av.article_json_hash = fragment_logic.hash_ajson(av.article_json_v1)
                    av.save()
                    # 13 of 152
                    print("%s of %s" % (i, num))
        except KeyboardInterrupt:
            print("ctrl-c caught")
            sys.exit(1)

        sys.exit(0)
