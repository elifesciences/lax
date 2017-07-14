#from mock import patch
from io import StringIO
import os, json  # , copy
from django.test import TestCase as DjangoTestCase, TransactionTestCase
from publisher import models, utils, ajson_ingestor
from django.core.management import call_command as dj_call_command
import unittest
from publisher.utils import renkeys, delall

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
            dj_call_command(*args, **kwargs)
        except SystemExit as err:
            return err.code, stdout.getvalue()
        self.fail("ingest script should always throw a systemexit()")

    def add_or_update_article(self, **adata):
        "creates article+article-version stubs for testing"
        replacements = [
            ('pub-date', 'published'),
            ('update', 'versionDate'),
        ]
        renkeys(adata, replacements)

        struct = {
            'id': utils.doi2msid(adata['doi']) if 'doi' in adata else adata['manuscript_id'],
            'volume': 1,
            'type': 'research-article',

            'title': '[default]',
            'version': 1,
            'status': models.VOR,
            'published': '2012-01-01T00:00:00Z'
        }
        struct.update(adata)        
        delall(struct, ['journal']) # can't be serialized, not utilised anyway
        
        with self.settings(VALIDATE_FAILS_FORCE=False):
            # bad ajson won't fail ingest
            av = ajson_ingestor.ingest_publish({'article': struct}, force=True)
            av.datetime_published = utils.todt(struct['published'])
            av.save()
            return av

#
#
#

class BaseCase(SimpleBaseCase, DjangoTestCase):
    pass

class TransactionBaseCase(SimpleBaseCase, TransactionTestCase):
    pass
