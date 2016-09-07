from os.path import join
import json
from base import BaseCase
from publisher import ajson_ingestor, models

class TestAJSONIngest(BaseCase):
    def setUp(self):
        self.ajson_fixture1 = join(self.fixture_dir, 'ajson', 'elife.01968.json')
        self.valid_ajson = json.load(open(self.ajson_fixture1, 'r'))

    def tearDown(self):
        pass
    
    def test_article_ingest(self):
        """valid article-json is successfully ingested, creating an article, 
        an article version and storing the ingestion request"""
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

        ajson_ingestor.ingest(self.valid_ajson)

        self.assertEqual(models.Journal.objects.count(), 1)
        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)

    def test_article_ingest_update(self):
        self.assertEqual(models.ArticleVersion.objects.count(), 0)
        _, _, av = ajson_ingestor.ingest(self.valid_ajson)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        self.assertEqual(av.title, self.valid_ajson['article']['title'])

        # do it again to cause an update
        expected_title = 'flub'
        self.valid_ajson['article']['title'] = expected_title
        _, _, av = ajson_ingestor.ingest(self.valid_ajson, update=True)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        self.assertEqual(av.title, expected_title)

    def test_article_ingest_bad_journal(self):
        self.assertEqual(models.ArticleVersion.objects.count(), 0)
        del self.valid_ajson['journal']
        self.assertRaises(Exception, ajson_ingestor.ingest, self.valid_ajson)
        
class TestAJSONPublish(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass
