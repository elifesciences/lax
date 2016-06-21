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
        self.update_fixture = join(self.fixture_dir, 'ppp', '00353.1', 'elife-00353-v1.json')

    def tearDown(self):
        pass

    def test_article_created(self):
        "an article can be imported from JSON"
        self.assertEqual(0, models.Article.objects.count())
        self.assertEqual(0, models.ArticleVersion.objects.count())
        ingestor.import_article_from_json_path(self.journal, self.json_fixture)
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.Article.objects.count())

    def test_article_not_created(self):
        "an exception is raised when attempting to import article data for a non-existant article when create=False"
        self.assertEqual(0, models.Article.objects.count())
        self.assertRaises(models.Article.DoesNotExist, ingestor.import_article_from_json_path, self.journal, self.json_fixture, create=False)
        self.assertEqual(0, models.Article.objects.count())

    def test_article_data(self):
        "the Article created from the json import has the correct data"
        expected_data = {
            #'title':  "A good life",
            'doi': "10.7554/eLife.00353",
            'journal': self.journal,
            'type': 'discussion'
        }
        dirty_article, ver = ingestor.import_article_from_json_path(self.journal, self.json_fixture)
        clean_article = models.Article.objects.get(pk=dirty_article.pk)
        for attr, expected_value in expected_data.items():
            self.assertEqual(getattr(clean_article, attr), expected_value)

    def test_article_version_data(self):
        art, ver = ingestor.import_article_from_json_path(self.journal, self.json_fixture)        
        expected_data = {
            'article': art,
            'datetime_published': utils.todt('2012-12-10'),
            'status': 'poa',
            'version': 1,
        }
        avobj = models.ArticleVersion.objects.get(article=art, version=1)
        for attr, expected in expected_data.items():
            self.assertEqual(getattr(avobj, attr), expected)

    def test_article_updated(self):
        "an article is successfully updated when update=True"
        self.assertEqual(0, models.Article.objects.count())
        art, ver = ingestor.import_article_from_json_path(self.journal, self.json_fixture)
        for attr, expected in [['title', "A meh life"],
                               ['status', "poa"],
                               ['version', 1],
                               ["datetime_published", utils.todt("2012-12-10")]]:
            self.assertEqual(getattr(ver, attr), expected)
        
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.Article.history.count())

        # attempt the update
        
        art, ver = ingestor.import_article_from_json_path(self.journal, self.update_fixture, update=True)
        for attr, expected in [['title', "A good life"],
                               ['status', "vor"],
                               ["datetime_published", utils.todt("2012-12-13")]]:
            self.assertEqual(getattr(ver, attr), expected)
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

    def test_article_import_update_of_many_versions(self):
        "three versions of the same article can be ingested with expected results"
        path = join(self.fixture_dir, "ppp-09066")
        v1 = join(path, "elife-09066-v1.json")
        v2 = join(path, "elife-09066-v2.json")
        v3 = join(path, "elife-09066-v3.json")
        
        ingestor.import_article_from_json_path(self.journal, v1)
        ingestor.import_article_from_json_path(self.journal, v2)
        ingestor.import_article_from_json_path(self.journal, v3)

        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 3)

        v1obj = models.ArticleVersion.objects.get(version=1) # POA
        v2obj = models.ArticleVersion.objects.get(version=2) # POA
        v3obj = models.ArticleVersion.objects.get(version=3) # VOR
        
        self.assertEqual(v1obj.datetime_published, utils.todt("2015-12-19T00:00:00Z"))
        self.assertEqual(v2obj.datetime_published, utils.todt("2015-12-23T00:00:00Z"))
        self.assertEqual(v3obj.datetime_published, utils.todt("2016-02-04T00:00:00Z"))

        # all three objects should share the same article and the article's date_published should be the
        # date of the earliest Article Version
        self.assertEqual(v1obj.datetime_published, v1obj.article.datetime_published)
        self.assertEqual(v1obj.datetime_published, v2obj.article.datetime_published)
        self.assertEqual(v1obj.datetime_published, v3obj.article.datetime_published)
        
class ImportArticleFromJSONViaAPI(BaseCase):
    def setUp(self):
        self.c = Client()
        doc = 'elife00353.xml.json'
        self.json_fixture = os.path.join(self.this_dir, 'fixtures', doc)

    def tearDown(self):
        pass

    def test_article_create_update_view(self):
        "an article can be created and updated via API using EIF"
        self.assertEqual(0, models.Article.objects.count())
        self.assertEqual(0, models.ArticleVersion.objects.count())
        json_data = open(self.json_fixture, 'r').read()
        data = json.loads(json_data)
        
        # create the article. 1xEIF == 1xArticle + 1xArticleVersion
        resp = self.c.post(reverse('api-create-update-article'), json_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.ArticleVersion.objects.count())

        # change the doi, ensure it's changed in the db
        updated_data = utils.updatedict(data, title='pants.party')
        logic.add_or_update_article(**updated_data)
        models.ArticleVersion.objects.get(title=updated_data['title'])

        # update the same article (with the original doi)
        resp = self.c.post(reverse('api-create-update-article'), json_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        
        # ensure nothing new has been created
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.ArticleVersion.objects.count())

        # ensure the article has been updated
        models.ArticleVersion.objects.get(title=data['title'])

    def test_article_create_update_multiple_versions_view(self):
        "an article can be imported from JSON via API across multiple versions"
        # setup
        self.assertEqual(0, models.Article.objects.count())
        json_data = open(self.json_fixture, 'r').read()
        data = json.loads(json_data)
        api_url = reverse('api-create-update-article')
        
        # post the article with a version of 1
        resp = self.c.post(api_url, json_data, content_type="application/json")
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.ArticleVersion.objects.count())

        # post a new version of same article with a version of 2
        data["version"] = "2"
        resp = self.c.post(api_url, json.dumps(data), content_type="application/json")
        self.assertEqual(200, resp.status_code)
        articles = models.Article.objects.filter(doi=data['doi'])
        versions = models.ArticleVersion.objects.filter(article__doi=data['doi'])
        self.assertEqual(1, articles.count())
        self.assertEqual(2, versions.count())

        # test the data
        v1, v2 = versions.all().order_by('version') # ordering is in models.py
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

        eif_update_fixture = join(self.fixture_dir, 'ppp', '00353.1', 'elife-00353-v1.json')
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

    '''
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
    '''

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
        eif_update_fixture = join(self.fixture_dir, 'ppp', '00353.1', 'elife-00353-v1.json')
        art, ver = ingestor.import_article_from_json_path(self.journal, fixture)
        self.assertEqual(ver.title, "A meh life")
        self.assertEqual(1, art.history.count()) # original art
        art, ver = ingestor.import_article_from_json_path(self.journal, eif_update_fixture, update=True)
        self.assertEqual(ver.title, "A good life")
        self.assertEqual(2, art.history.count()) # original + updated art
