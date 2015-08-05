import os, json
from publisher import ingestor, utils, models, logic
from base import BaseCase
import logging
from publisher import views

from django.test import Client
from django.core.urlresolvers import reverse

logging.getLogger("").setLevel(logging.WARNING) # suppresses debug, info messages

class ImportArticleFromJSON(BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        doc = 'elife00005.xml.json'
        self.json_fixture = os.path.join(self.this_dir, 'fixtures', doc)

    def tearDown(self):
        pass

    def test_article_created(self):
        "an article can be imported from JSON"
        self.assertEqual(0, models.Article.objects.count())
        ingestor.import_article_from_json_path(self.journal, self.json_fixture)
        self.assertEqual(1, models.Article.objects.count())

    def test_article_data(self):
        "the created Article from json import has the correct data"
        expected_data = {
            'title':  "Molecular architecture of human polycomb repressive complex 2",
            'version': 1,
            'doi': "10.7554/eLife.00005",
            'journal': self.journal,
        }
        dirty_article = ingestor.import_article_from_json_path(self.journal, self.json_fixture)
        clean_article = models.Article.objects.get(pk=dirty_article.pk)
        for attr, expected_value in expected_data.items():
            self.assertEqual(getattr(clean_article, attr), expected_value)


class ImportArticleFromJSONViaAPI(BaseCase):
    def setUp(self):
        self.c = Client()
        doc = 'elife00005.xml.json'
        self.json_fixture = os.path.join(self.this_dir, 'fixtures', doc)

    def tearDown(self):
        pass

    def test_article_created_view(self):
        "an article can be import from JSON via a view"
        self.assertEqual(0, models.Article.objects.count())
        json_data = open(self.json_fixture, 'r').read()
        resp = self.c.post(reverse('api-import-article'), json_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.Article.objects.count())

        # TODO: test the data correctness!!!

    def test_article_created_view_with_bad_payload(self):
        "the view raises a 400 error if the given payload cannot be deserialized from json"
        pass

    def test_article_created_view_with_incorrect_payload(self):
        "the view raises a 400 error if the given payload does not contain the data we expect"
        pass

class ImportArticleFromRepo(BaseCase):
    def setUp(self):
        self.journal = logic.journal()

    def tearDown(self):
        pass

    def test_article_imported_lazily(self):
        self.assertEqual(0, models.Article.objects.count())
        # https://github.com/elifesciences/elife-article-json/blob/master/article-json/elife00654.xml.json
        doi = "10.7554/eLife.00654"
        expected_title = "Single molecule imaging reveals a major role for diffusion in the exploration of ciliary space by signaling receptors"
        dirty_article_obj = ingestor.import_article_from_github_repo(self.journal, doi)
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(dirty_article_obj.title, expected_title)
        clean_article_obj = models.Article.objects.get(doi=doi)
        self.assertEqual(clean_article_obj.title, expected_title)
        
class ImportArticleFromRepoLazilyUsingAPI(BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_article_info_using_lazily_fetched_article(self):
        # https://github.com/elifesciences/elife-article-json/blob/master/article-json/elife00654.xml.json
        doi = "10.7554/eLife.00654"
        expected_title = "Single molecule imaging reveals a major role for diffusion in the exploration of ciliary space by signaling receptors"
        
        self.assertEqual(0, models.Article.objects.count())
        resp = self.c.get(reverse("api-article", kwargs={'doi': doi}))
        self.assertEqual(1, models.Article.objects.count())
        
        clean_article = models.Article.objects.get(doi=doi)
        self.assertEqual(resp.data, views.ArticleSerializer(clean_article).data)
