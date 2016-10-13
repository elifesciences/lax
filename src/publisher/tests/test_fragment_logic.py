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
        _, _, self.av = ajson_ingestor.ingest_publish(self.ajson)

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

    def test_update_fragment(self):
        "a fragment of article data can be updated by adding it again with different content"

        # ensure we have something that resembles the ingest data
        self.assertEqual(models.ArticleFragment.objects.count(), 1)
        frag = logic.get(self.av, 'xml->json')
        self.assertTrue('article' in frag)

        # now update it with some garbage
        data = {'article': {'title': 'pants-party'}}
        logic.add(self.av, 'xml->json', data, pos=0, update=True)

        # ensure we've just destroyed our very important data
        frag = logic.get(self.av, 'xml->json')
        self.assertEqual(frag, data)

    def test_delete_fragment(self):
        self.assertEqual(models.ArticleFragment.objects.count(), 1)
        fragment = {'title': 'pants. party'}
        logic.add(self.msid, 'foo', fragment)
        self.assertEqual(models.ArticleFragment.objects.count(), 2)
        logic.rm(self.msid, 'foo')
        self.assertEqual(models.ArticleFragment.objects.count(), 1)

class FragmentMerge(BaseCase):
    def setUp(self):
        self.ajson_fixture = join(self.fixture_dir, 'ajson', 'elife.01968.json')
        self.ajson = json.load(open(self.ajson_fixture, 'r'))
        self.msid = self.ajson['article']['id']
        self.version = self.ajson['article']['version'] # v1
        _, _, self.av = ajson_ingestor.ingest_publish(self.ajson)

    def test_merge_fragments(self):
        logic.add(self.av, 'xml->json', {'article': {'title': 'foo'}}, update=True)

        logic.add(self.msid, 'frag1', {'body': 'bar'})
        logic.add(self.msid, 'frag2', {'foot': 'baz'})

        expected = {'title': 'foo', 'body': 'bar', 'foot': 'baz'}
        self.assertEqual(expected, logic.merge(self.av))
