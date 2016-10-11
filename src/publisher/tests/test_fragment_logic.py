from os.path import join
import json
from base import BaseCase
from publisher import fragment_logic as logic, ajson_ingestor, models

"""
ingesting an article creates our initial ArticleFragment, the 'xml->json' fragment
at position 0.

all other fragments are merged into this initial fragment

the result is valid article json

"""

class ArticleIngestFragmentLogic(BaseCase):
    def setUp(self):
        self.ajson_fixture = join(self.fixture_dir, 'ajson', 'elife.01968.json')
        self.ajson = json.load(open(self.ajson_fixture, 'r'))
        self.msid = self.ajson['article']['id']
        self.version = self.ajson['article']['version'] # v1

    def test_ajson_ingest_creates_article_fragment(self):
        self.assertEqual(models.ArticleFragment.objects.count(), 0)
        ajson_ingestor.ingest(self.ajson)
        self.assertEqual(models.ArticleFragment.objects.count(), 1)

class FragmentLogic(BaseCase):
    def setUp(self):
        self.ajson_fixture = join(self.fixture_dir, 'ajson', 'elife.01968.json')
        self.ajson = json.load(open(self.ajson_fixture, 'r'))
        self.msid = self.ajson['article']['id']
        self.version = self.ajson['article']['version'] # v1

        # populate with an article. CREATES A FRAGMENT
        ajson_ingestor.ingest_publish(self.ajson)

    def tearDown(self):
        pass

    def test_add_fragment(self):
        "a fragment of article data can be recorded against an Article"
        # `setUp` creates a fragment by ingesting article
        self.assertEqual(models.ArticleFragment.objects.count(), 1)

        fragment = {'title': 'pants. party'}
        fragobj = logic.add(self.msid, 'foo', fragment)
        self.assertEqual(models.ArticleFragment.objects.count(), 2)
        self.assertEqual(fragment, fragobj.fragment)

    def test_delete_fragment(self):
        self.assertEqual(models.ArticleFragment.objects.count(), 1)
        fragment = {'title': 'pants. party'}
        logic.add(self.msid, 'foo', fragment)
        self.assertEqual(models.ArticleFragment.objects.count(), 2)
        logic.rm(self.msid, 'foo')
        self.assertEqual(models.ArticleFragment.objects.count(), 1)
