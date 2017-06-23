from io import StringIO
import os, json, copy
from django.test import TestCase as DjangoTestCase, TransactionTestCase
from publisher import models, utils
from django.core.management import call_command
import unittest

'''
def filldict(ddict, keys, default):
    def filldictslot(ddict, key, val):
        if key not in ddict:
            ddict[key] = val
    data = copy.deepcopy(ddict)
    for key in keys:
        if isinstance(key, tuple):
            key, val = key
        else:
            val = default
        filldictslot(data, key, val)
    return data

def add_or_update_article(**article_data):
    """TESTING ONLY. given article data it attempts to find the
    article and update it, otherwise it will create it, filling
    any missing keys with dummy data. returns the created article."""
    assert 'doi' in article_data or 'manuscript_id' in article_data, \
        "a value for 'doi' or 'manuscript_id' *must* exist"

    if 'manuscript_id' in article_data:
        article_data['doi'] = utils.msid2doi(article_data['manuscript_id'])
    elif 'doi' in article_data:
        article_data['manuscript_id'] = utils.doi2msid(article_data['doi'])

    filler = [
        'title',
        'doi',
        'manuscript_id',
        ('volume', 1),
        'path',
        'article-type',
        ('ejp_type', 'RA'),
        ('version', 1),
        ('pub-date', '2012-01-01'),
        ('status', 'vor'),
    ]
    article_data = utils.filldict(article_data, filler, 'pants-party')
    # return eif_ingestor.import_article(journal(), article_data, create=True, update=True)
    return article_data

'''

#
#
#

class SimpleBaseCase(unittest.TestCase):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    fixture_dir = os.path.join(this_dir, 'fixtures')
    maxDiff = None

    # eh - not sure about this. can I patch entire classes
    # to turn auto-stubbing off??
    def load_ajson(self, path, strip_relations=True):
        "loads an article-json fixture. conveniently strips relations by default"
        data = json.load(open(path, 'r'))
        if strip_relations:
            # remove these values here so they don't interfere in creation
            utils.delall(data['article'], ['-related-articles-internal', '-related-articles-external'])
        return data

    def freshen(self, obj):
        return utils.freshen(obj)

    def unpublish(self, msid, version=None):
        "'unpublishes' an article"
        if not version:
            # unpublish *all* versions of an article
            for av in models.Article.objects.get(manuscript_id=msid).articleversion_set.all():
                av.datetime_published = None
                av.save()
        else:
            av = models.ArticleVersion.objects.get(article__manuscript_id=msid, version=version)
            av.datetime_published = None
            av.save()

    def call_command(self, *args, **kwargs):
        stdout = StringIO()
        try:
            kwargs['stdout'] = stdout
            call_command(*args, **kwargs)
        except SystemExit as err:
            return err.code, stdout.getvalue()
        self.fail("ingest script should always throw a systemexit()")

#
#
#

class BaseCase(SimpleBaseCase, DjangoTestCase):
    pass

class TransactionBaseCase(SimpleBaseCase, TransactionTestCase):
    pass
