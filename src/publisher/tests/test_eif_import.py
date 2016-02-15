import os, json
from os.path import join
from publisher import ingestor, utils, models, logic
from base import BaseCase
import logging
from publisher import views
import json
from django.test import Client
from django.core.urlresolvers import reverse

logging.getLogger("").setLevel(logging.WARNING) # suppresses debug, info messages

class ImportArticleFromJSON(BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        doc = 'elife00353.xml.json'
        self.json_fixture = os.path.join(self.this_dir, 'fixtures', doc)
        self.update_fixture = join(self.fixture_dir, 'ppp', '00353.1', '2d3245f7-46df-4c14-b8c2-0bb2f1731ba4', 'elife-00353-v1.json')

    def tearDown(self):
        pass

    def test_article_created(self):
        "an article can be imported from JSON"
        self.assertEqual(0, models.Article.objects.count())
        ingestor.import_article_from_json_path(self.journal, self.json_fixture)
        self.assertEqual(1, models.Article.objects.count())

    def test_article_not_created(self):
        "an exception is raised when attempting to import article data for a non-existant article when create=False"
        self.assertEqual(0, models.Article.objects.count())
        self.assertRaises(models.Article.DoesNotExist, ingestor.import_article_from_json_path, self.journal, self.json_fixture, create=False)
        self.assertEqual(0, models.Article.objects.count())

    def test_article_data(self):
        "the created Article from json import has the correct data"
        expected_data = {
            'title':  "A good life",
            'version': 1,
            'doi': "10.7554/eLife.00353",
            'journal': self.journal,
        }
        dirty_article = ingestor.import_article_from_json_path(self.journal, self.json_fixture)
        clean_article = models.Article.objects.get(pk=dirty_article.pk)
        for attr, expected_value in expected_data.items():
            self.assertEqual(getattr(clean_article, attr), expected_value)


    def test_article_updated(self):
        "an article is successfully updated when update=True"
        self.assertEqual(0, models.Article.objects.count())
        art = ingestor.import_article_from_json_path(self.journal, self.json_fixture)
        self.assertEqual(art.title, "A good life")
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.Article.history.count())

        # attempt the update
        art = ingestor.import_article_from_json_path(self.journal, self.update_fixture, update=True)
        self.assertEqual(art.title, "A meh life")
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(2, models.Article.history.count())

    def test_article_not_updated(self):
        "an exception is raised when attempting to import article data for an existing article when update=False"
        self.assertEqual(0, models.Article.objects.count())
        ingestor.import_article_from_json_path(self.journal, self.json_fixture)
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.Article.history.count())
        
        # attempt the update
        self.assertRaises(AssertionError, ingestor.import_article_from_json_path, self.journal, self.json_fixture, update=False)
        self.assertEqual(1, models.Article.history.count())

    def test_article_update_when_doesnt_exist(self):
        # attempt the update
        self.assertRaises(models.Article.DoesNotExist, ingestor.import_article_from_json_path, self.journal, self.json_fixture, create=False, update=True)
        self.assertEqual(0, models.Article.history.count())

class ImportArticleFromJSONViaAPI(BaseCase):
    def setUp(self):
        self.c = Client()
        doc = 'elife00353.xml.json'
        self.json_fixture = os.path.join(self.this_dir, 'fixtures', doc)

    def tearDown(self):
        pass

    def test_article_create_update_view(self):
        "an article can be import from JSON via API"
        self.assertEqual(0, models.Article.objects.count())
        json_data = open(self.json_fixture, 'r').read()
        data = json.loads(json_data)
        
        resp = self.c.post(reverse('api-create-update-article'), json_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.Article.objects.count())

        # change the doi
        artobj = models.Article.objects.all()[0]
        artobj.title = 'pants.party'
        artobj.save()

        models.Article.objects.get(title='pants.party')

        # update the same article (with the original doi)
        resp = self.c.post(reverse('api-create-update-article'), json_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.Article.objects.count())

        artobj = models.Article.objects.all()[0]
        self.assertEqual(artobj.title, data['title'])

    def test_article_create_update_multiple_versions_view(self):
        "an article can be imported from JSON via API across multiple versions"
        self.assertEqual(0, models.Article.objects.count())
        json_data = open(self.json_fixture, 'r').read()
        data = json.loads(json_data)
        
        # post the article with a version of 1
        resp = self.c.post(reverse('api-create-update-article'), json_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.Article.objects.count())

        # post a new version of same article with a version of 2
        data["version"] = "2"
        json_data = json.dumps(data)
        resp = self.c.post(reverse('api-create-update-article'), json_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        q = models.Article.objects.filter(doi=data['doi'])
        self.assertEqual(2, q.count())

        v1, v2 = q.all() # ordering is in models.py
        self.assertEqual(v1.version, 1)
        self.assertEqual(v2.version, 2)

    def test_article_created_view(self):
        "an article can be import from JSON via API"
        self.assertEqual(0, models.Article.objects.count())
        json_data = open(self.json_fixture, 'r').read()
        resp = self.c.post(reverse('api-create-article'), json_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.Article.objects.count())

        # TODO: test the data correctness!!!

    def test_article_multiple_creates(self):
        "multiple attempts to create the same article fail after initial with 400 (Bad Request)"
        self.assertEqual(0, models.Article.objects.count())
        json_data = open(self.json_fixture, 'r').read()
        resp = self.c.post(reverse('api-create-article'), json_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.Article.objects.count())

        resp = self.c.post(reverse('api-create-article'), json_data, content_type="application/json")
        self.assertEqual(400, resp.status_code)
        self.assertEqual(1, models.Article.objects.count())

    def test_article_updated_view(self):
        "an article can be updated by importing from JSON via API"
        json_data = open(self.json_fixture, 'r').read()
        resp = self.c.post(reverse('api-create-article'), json_data, content_type="application/json")
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.Article.history.count())
        self.assertEqual(200, resp.status_code)

        eif_update_fixture = join(self.fixture_dir, 'ppp', '00353.1', '2d3245f7-46df-4c14-b8c2-0bb2f1731ba4', 'elife-00353-v1.json')
        json_update_data = open(eif_update_fixture, 'r').read()
        resp = self.c.post(reverse('api-update-article'), json_update_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(2, models.Article.history.count())

    def test_article_created_view_with_bad_payload(self):
        "the view raises a 400 error if the given payload cannot be deserialized from json"
        json_data = "paaaaaaaaaaaaaaaaaaaaants party"
        resp = self.c.post(reverse('api-create-article'), json_data, content_type="application/json")
        self.assertEqual(400, resp.status_code)
        self.assertEqual(0, models.Article.objects.count())

    def test_article_created_view_with_incorrect_payload(self):
        "the view raises a 400 error if the given payload does not contain the data we expect"
        invalid_json_list = [
            # empty
            "{}",
            "[]",
             # missing actual data
            '["pants"]',
            '{"pants": "party"}',
            # partial data
            '{"title": "pants party", "version": 1}',
        ]
        for bad_data in invalid_json_list:
            try:
                resp = self.c.post(reverse('api-create-article'), bad_data, content_type="application/json")
                self.assertEqual(400, resp.status_code)
                self.assertEqual(0, models.Article.objects.count())
            except AssertionError, e:
                print '>>> ', bad_data
                print e
                raise

    def test_article_update_when_doesnt_exist(self):
        # attempt the update
        json_data = open(self.json_fixture, 'r').read()
        resp = self.c.post(reverse('api-update-article'), json_data, content_type="application/json")
        self.assertEqual(404, resp.status_code)
        self.assertEqual(0, models.Article.objects.count())



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

    def test_article_import_bad_doi(self):
        self.assertEqual(0, models.Article.objects.count())
        doi = "10.7554/no.pants"
        self.assertRaises(ValueError, ingestor.import_article_from_github_repo, self.journal, doi)
        # nothing created
        self.assertEqual(0, models.Article.objects.count())

    def test_article_import_no_doi(self):
        self.assertEqual(0, models.Article.objects.count())
        doi = None
        self.assertRaises(ValueError, ingestor.import_article_from_github_repo, self.journal, doi)
        # nothing created
        self.assertEqual(0, models.Article.objects.count())




class ImportFromPPPEIF(BaseCase):
    """the EIF article json floating around the PPP workflow
    differs from the more predictable stuff that can be found at
    github.com/elifesciences/elife-article-json"""
    
    def setUp(self):
        self.fixture_list = []
        self.journal = logic.journal()
        for dirpath, _, files in os.walk(join(self.fixture_dir, 'ppp')):
            if not files: continue
            self.fixture_list.extend(map(lambda f: os.path.join(dirpath, f), files))

    def tearDown(self):
        pass

    def test_ppp_basic_import(self):
        "ppp eif can be imported without exceptions"
        for fixture in self.fixture_list:
            ingestor.import_article_from_json_path(self.journal, fixture)

    def test_ppp_update(self):
        "ppp eif can be used to update existing article without exceptions"
        fixture = join(self.fixture_dir, 'elife00353.xml.json')
        eif_update_fixture = join(self.fixture_dir, 'ppp', '00353.1', '2d3245f7-46df-4c14-b8c2-0bb2f1731ba4', 'elife-00353-v1.json')
        art = ingestor.import_article_from_json_path(self.journal, fixture)
        self.assertEqual(art.title, "A good life")
        self.assertEqual(1, art.history.count()) # original art
        art = ingestor.import_article_from_json_path(self.journal, eif_update_fixture, update=True)
        self.assertEqual(art.title, "A meh life")
        self.assertEqual(2, art.history.count()) # original + updated art


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

    def test_article_bad_doi(self):
        doi = "10.7554/paaaaaaaaaaaaaants.party"
        self.assertEqual(0, models.Article.objects.count())        
        resp = self.c.get(reverse("api-article", kwargs={'doi': doi}))
        # nothing is imported
        self.assertEqual(0, models.Article.objects.count())
        # 'not found' given
        self.assertEqual(404, resp.status_code)
