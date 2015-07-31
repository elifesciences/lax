import os, json
from publisher import ingestor, utils, models, logic
from base import BaseCase
import logging

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
        

class ArticleInfoViaApi(BaseCase):
    def setUp(self):
        self.c = Client()
        self.journal = logic.journal()

        article_data = {
            'title':  "Molecular architecture of human polycomb repressive complex 2",
            'version': 1,
            'doi': "10.7554/eLife.00005",
            'journal': self.journal,
        }
        article = models.Article(**article_data)
        article.save()
        self.article = article

    def tearDown(self):
        pass

    def test_article_info_api(self):
        "article data returned by the api is the same as what is serialize"
        from publisher import views
        resp = self.c.get(reverse("api-article", kwargs={'doi': self.article.doi}))
        self.assertEqual(resp.data, views.ArticleSerializer(self.article).data)







class ArticleAttributeCreation(BaseCase):
    def setUp(self):
        self.journal = logic.journal()    
        article_data = {
            'title':  "Molecular architecture of human polycomb repressive complex 2",
            'version': 1,
            'doi': "10.7554/eLife.00005",
            'journal': self.journal,
        }
        article = models.Article(**article_data)
        article.save()
        self.article = article

        self.attribute_data = {
            'name': "Publication Date",
            'type': 'datetime',
            'description': "date and time of an article's publication. time component is optional and defaults to 00:00:00"
        }

    def tearDown(self):
        pass

    def test_create_attribute(self):
        "attributes can be created"
        self.assertEqual(0, models.AttributeType.objects.count())        
        dirty_attr = logic.create_attribute(**self.attribute_data)
        self.assertEqual(1, models.AttributeType.objects.count())

    def test_attribute_correctness(self):
        "the data of a newly created attribute is what we expect"
        dirty = logic.create_attribute(**self.attribute_data)
        clean = models.AttributeType.objects.get(pk=dirty.id)
        for key, expected_val in self.attribute_data.items():
            self.assertEqual(getattr(clean, key), expected_val)

    def test_add_article_attribute(self):
        "attributes can be added to an Article"
        self.assertEqual(0, models.ArticleAttribute.objects.count())
        logic.add_attribute_to_article(self.article, "foo", "bar", extant_only=False)
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        
    def test_add_article_attribute_data(self):
        "arbitrary attributes can be added to an Article"
        dirty_attr = logic.add_attribute_to_article(self.article, "foo", "bar", extant_only=False)
        clean_attr = models.ArticleAttribute.objects.get(pk=dirty_attr.id)
        self.assertEqual(clean_attr.key.name, "foo")
        self.assertEqual(clean_attr.key.type, models.DEFAULT_ATTR_TYPE)
        self.assertEqual(clean_attr.value, "bar")

    def test_add_article_attribute_strict(self):
        "attributes cannot be added to an Article unless attribute type already exists"
        self.assertRaises(models.AttributeType.DoesNotExist, logic.add_attribute_to_article, self.article, "foo", "bar")

class ArticleAttributionCreationViaAPI(BaseCase):
    def setUp(self):
        self.c = Client()
        doc = 'elife00005.xml.json'
        self.json_fixture = os.path.join(self.this_dir, 'fixtures', doc)

    def tearDown(self):
        pass

    def test_add_attribute_to_article_view(self):
        article_data = json.load(open(self.json_fixture, 'r'))
        expected_data = {
            'key': 'Article Type',
            'val': article_data['article-type'],
        }
        # create the article
        dirty_article = ingestor.import_article(logic.journal(), article_data)
        
        # create the expected AttributeType
        logic.create_attribute(name=expected_data['key'], type=models.DEFAULT_ATTR_TYPE)

        # craft the url
        kwargs = utils.subdict(article_data, ['doi'])
        resp = self.c.post(reverse('api-article-attribute', kwargs=kwargs), json.dumps(expected_data), content_type='application/json')
        
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        self.assertEqual(1, models.AttributeType.objects.count())
        
        # TODO: test the data correctness!!!

    def test_add_attribute_to_article_view_with_bad_payload(self):
        "the view should raise a 400 error if the payload cannot be deserialized from json"
        pass

    def test_add_attribute_to_article_view_with_incorrect_payload(self):
        "the view should raise a 400 error if the payload doesn't contain the values we expect"
        pass
