from os.path import join
from base import BaseCase
from publisher import ajson_ingestor, models

class TestAJSONIngest(BaseCase):
    def setUp(self):
        self.ajson_fixture1 = join(self.fixture_dir, 'ajson', 'elife.01968.json')

    def tearDown(self):
        pass

    def test_article_json_ingest(self):
        """valid article-json is successfully ingested, creating an article, 
        an article version and storing the ingestion request"""
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)
        valid_ajson = open(self.ajson_fixture1, 'r')
        ajson_ingestor.ingest_json(valid_ajson.read())
        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
