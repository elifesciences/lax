import sys
from functools import partial
from modcommand import ModCommand
from publisher.utils import boolkey
from publisher import models, fragment_logic
import logging

LOG = logging.getLogger('')
LOG.setLevel(logging.CRITICAL)

def do(avl):
    results = map(fragment_logic.revalidate, avl)
    # count ??
    return str(results)

def revalidate_specific_article_version(msid, ver):
    LOG.debug('revalidating article version %s %s', msid, ver)
    return do(models.ArticleVersion.objects.filter(article__manuscript_id=msid, version=ver))

def revalidate_all_versions_of_article(msid):
    LOG.debug('revalidating all versions of %s', msid)
    return do(models.ArticleVersion.objects.filter(article__manuscript_id=msid))

def revalidate_all_article_versions():
    LOG.debug('revalidating ALL articles')
    return do(models.ArticleVersion.objects.all())

class Command(ModCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument('--id', dest='msid', type=int)
        parser.add_argument('--version', dest='version', type=int)

        self.parser = parser

    def invalid_args(self, message):
        self.parser.error(message)
        sys.exit(1)

    def handle(self, *args, **options):
        msid, version = options.get('msid'), options.get('version')
        matrix = {
            # msid?, version?
            (True, True): partial(revalidate_specific_article_version, msid, version),
            (True, False): partial(revalidate_all_versions_of_article, msid),
            (False, False): revalidate_all_article_versions,

            (False, True): partial(self.invalid_args, "an '--id' must be provided if a '--version' is supplied")
        }
        return matrix[boolkey(msid, version)]()
