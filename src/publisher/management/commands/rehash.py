from publisher import models, fragment_logic
from django_tqdm import BaseCommand

# from django.core.management.base import BaseCommand
import sys
import logging
from django.db import transaction

LOG = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "calculates the hash for the stored article-json. completes in less than 2 mins"
    )

    def handle(self, *args, **options):
        t = self.tqdm()
        try:
            with transaction.atomic():
                # poa then vor articles. expect slowdown at about 36%
                q = models.ArticleVersion.objects.all().order_by("status")
                t.total = q.count()
                for (
                    av
                ) in (
                    q.iterator()
                ):  # .iterator() to use server-side cursor and avoid thrashing memory
                    av.article_json_hash = fragment_logic.hash_ajson(av.article_json_v1)
                    av.save()
                    t.update(1)
                t.info("done")
        except KeyboardInterrupt:
            t.error("ctrl-c caught")
            sys.exit(1)

        sys.exit(0)
