import os, glob, pprint
from django.core.management.base import BaseCommand
from publisher import logic, models

import logging
logger = logging.getLogger(__name__)

# does this even work?
class Command(BaseCommand):
    help = 'Checks each of the dois it can find'

    def handle(self, *args, **kwargs):
        for article in models.Article.objects.all():
            if article.doi:
                logic.check_doi(article.doi)
