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

    def test_article_ingest_does_not_publish(self):
        """ingesting article json does not cause an article to become published 
        (gain a published date) even if a published date was supplied"""
        expected = "2016-04-13T01:00:00"
        self.valid_ajson['article']['published'] = expected
        _, _, av = ajson_ingestor.ingest(self.valid_ajson)
        self.assertNotEqual(av.datetime_published, expected)

    def test_article_ingest_update(self):
        "ingesting article data twice successfully updates the article"
        _, _, av = ajson_ingestor.ingest(self.valid_ajson)

        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        self.assertEqual(av.title, self.valid_ajson['article']['title'])
        self.assertEqual(av.datetime_published, None) # not published

        # do it again to cause an update
        expected_title = 'flub'
        self.valid_ajson['article']['title'] = expected_title
        _, _, av = ajson_ingestor.ingest(self.valid_ajson)

        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        self.assertEqual(av.title, expected_title)
        self.assertEqual(av.datetime_published, None) # still not published

    def test_article_update_does_not_publish(self):
        "ingesting article data twice still does not cause publication"
        _, _, av = ajson_ingestor.ingest(self.valid_ajson)
        self.assertEqual(av.datetime_published, None)

        expected = "2016-04-13T01:00:00"
        self.valid_ajson['article']['published'] = expected

        _, _, av = ajson_ingestor.ingest(self.valid_ajson)
        self.assertEqual(av.datetime_published, None)

    def test_article_ingest_fails_for_published_articles(self):
        "ingesting article data for a published article version fails"
        assert False

    def test_article_ingest_for_published_articles_succeeds_if_forced(self):
        "ingesting article data for a published article version succeeds if force=True"
        assert False

    #

    def test_article_ingest_bad_journal(self):
        self.assertEqual(models.Journal.objects.count(), 0)
        del self.valid_ajson['journal']
        self.assertRaises(Exception, ajson_ingestor.ingest, self.valid_ajson)
        self.assertEqual(models.Journal.objects.count(), 0)

class TestAJSONPublish(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_article_publish(self):
        assert False

    def test_article_publish_fails_if_already_published(self):
        assert False
