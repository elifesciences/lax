import os, json
from publisher import ingestor, utils, models, logic, views
from base import BaseCase
import logging

from django.test import Client
from django.core.urlresolvers import reverse

logging.getLogger("").setLevel(logging.WARNING) # suppresses debug, info messages

class ArticleLogic(BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        self.article_data = {
            'title':  "Molecular architecture of human polycomb repressive complex 2",
            'version': 1,
            'doi': "10.7554/eLife.00005",
            'journal': self.journal,
        }

    def tearDown(self):
        pass

    def test_fetch_article(self):
        self.assertEqual(0, models.Article.objects.count())
        dirty_art = logic.article(self.article_data['doi'])
        self.assertEqual(1, models.Article.objects.count())

    def test_fetch_nonexistant_article(self):
        self.assertEqual(0, models.Article.objects.count())
        self.assertRaises(models.Article.DoesNotExist, logic.article, 'paaaaaaaaan/t.s')
        self.assertEqual(0, models.Article.objects.count())

    def test_fetches_latest_always(self):
        "when version is not specified, `logic.article` returns the latest"
        self.assertEqual(0, models.Article.objects.count())
        article_data_list = [
            {'title': 'foo',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},
             
            {'title': 'bar',
             'version': 2,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},

            {'title': 'baz',
             'version': 3,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        self.assertEqual(3, models.Article.objects.count())
        
        art = logic.article("10.7554/eLife.DUMMY")
        self.assertEqual(art.version, 3)
        self.assertEqual(art.title, 'baz')

    def test_fetch_historical(self):
        "previous versions of an article's changes are available in history"
        self.assertEqual(0, models.Article.objects.count())
        article_data_list = [
            {'title': 'foo',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},
             
            {'title': 'bar',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},

            {'title': 'baz',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        self.assertEqual(1, models.Article.objects.count())
        
        art = models.Article.objects.get(doi="10.7554/eLife.DUMMY", version=1)
        self.assertEqual(3, art.history.count())

        # check the data inserted vs the data returned
        for expected, historical_art in zip(article_data_list, art.history.all().order_by('version')):
            for attr in ['title', 'version']:
                self.assertEqual(expected[attr], getattr(historical_art, attr))

    def test_fetch_specific_historical(self):
        "a specific previous version of an article's changes can be fetched from history"
        self.assertEqual(0, models.Article.objects.count())
        article_data_list = [
            {'title': 'foo',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},
             
            {'title': 'bar',
             'version': 2,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},

            {'title': 'baz',
             'version': 3,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        self.assertEqual(3, models.Article.objects.count())
        
        expected_version = 2
        art = logic.article("10.7554/eLife.DUMMY", expected_version)
        self.assertEqual(art.version, expected_version)
        self.assertEqual(art.title, 'bar')

    def test_fetch_specific_historical_when_multiple_of_same_version(self):
        """a specific previous version of an article's changes can be fetched
        from history, even when there are multiple articles in history with the
        same version number"""
        self.assertEqual(0, models.Article.objects.count())
        article_data_list = [
            {'title': 'foo',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},
             
            {'title': 'bar',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},

            {'title': 'baz',
             'version': 2,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},

            {'title': 'bup',
             'version': 3,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},

            {'title': 'boo',
             'version': 3,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        self.assertEqual(3, models.Article.objects.count())
        
        expected_version = 1
        art = logic.article("10.7554/eLife.DUMMY", expected_version)
        self.assertEqual(art.version, expected_version)
        self.assertEqual(art.title, 'bar')
        self.assertEqual(logic.article("10.7554/eLife.DUMMY", 2).title, 'baz')
        self.assertEqual(logic.article("10.7554/eLife.DUMMY", 3).title, 'boo')


class ArticleInfoViaApi(BaseCase):
    def setUp(self):
        self.c = Client()
        self.journal = logic.journal()
        self.article_data = {
            'title':  "Molecular architecture of human polycomb repressive complex 2",
            'version': 1,
            'doi': "10.7554/eLife.00005",
            'journal': self.journal,
        }

    def tearDown(self):
        pass

    def test_article_info_api(self):
        "article data returned by the api is the same as what is serialize"        
        article = models.Article(**self.article_data)
        article.save()        
        resp = self.c.get(reverse("api-article", kwargs={'doi': article.doi}))
        self.assertEqual(resp.data, views.ArticleSerializer(article).data)

    def test_article_info_api_no_article(self):
        "non existant articles raise a 404"
        doi = 'paaaaaaaaan/t.s'
        resp = self.c.get(reverse("api-article", kwargs={'doi': doi}))
        self.assertEqual(resp.status_code, 404)

    def test_article_info_api_case_insensitive(self):
        "article data returned by the api is the same as what is serialize"
        kwargs = self.article_data
        kwargs['doi'] = kwargs['doi'].upper()
        article = models.Article(**kwargs)
        article.save()        
        resp = self.c.get(reverse("api-article", kwargs={'doi': article.doi}))
        self.assertEqual(resp.data, views.ArticleSerializer(article).data)

    def test_article_info_version_grouping_no_art(self):
        doi = 'paaaaaaaaan/t.s'
        resp = self.c.get(reverse("api-article-versions", kwargs={'doi': doi}))
        self.assertEqual(404, resp.status_code)

    def test_article_info_version_grouping(self):
        "test that an article with multiple versions is returned"
        doi = "10.7554/eLife.DUMMY"
        article_data_list = [
            {'title': 'foo',
             'version': 1,
             'doi': doi,
             'journal': self.journal},
             
            {'title': 'bar',
             'version': 2,
             'doi': doi, 
             'journal': self.journal},

            {'title': 'baz',
             'version': 3,
             'doi': doi,
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        
        self.assertEqual(3, models.Article.objects.count())
        
        resp = self.c.get(reverse("api-article-versions", kwargs={'doi': doi}))
        data = resp.data
        self.assertEqual([1, 2, 3], data.keys())
        for expected_item in article_data_list:
            resp_item = data[expected_item['version']]
            self.assertEqual(resp_item['title'], expected_item['title'])
            self.assertEqual(resp_item['version'], expected_item['version'])
            self.assertEqual(resp_item['doi'], expected_item['doi'])

    def test_article_info_version(self):
        "test that the correct article version is returned when specified via the api"
        doi = "10.7554/eLife.DUMMY"
        article_data_list = [
            {'title': 'foo',
             'version': 1,
             'doi': doi,
             'journal': self.journal},
             
            {'title': 'bar',
             'version': 1,
             'doi': doi, 
             'journal': self.journal},

            {'title': 'baz',
             'version': 2,
             'doi': doi,
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        
        expected_version = 1
        resp = self.c.get(reverse("api-article", kwargs={'doi': doi, 'version': expected_version}))
        self.assertEqual(2, models.Article.objects.count())
        self.assertEqual(resp.data['version'], expected_version)
        self.assertEqual(resp.data['title'], 'bar')

        


    #
    # corpus
    #

    def test_article_corpus_api(self):
        self.assertEqual(0, models.Article.objects.count())
        resp = self.c.get(reverse("api-corpus-info"))
        self.assertEqual(resp.data, {'article-count': 0,
                                     'research-article-count': 0})
        
        article = models.Article(**self.article_data)
        article.save()
        self.assertEqual(1, models.Article.objects.count())
        resp = self.c.get(reverse("api-corpus-info"))
        self.assertEqual(resp.data, {'article-count': 1,
                                     'research-article-count': 0})
        


class ArticleAttribute(BaseCase):
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

    def tearDown(self):
        pass

    def test_create_attribute(self):
        "attributes can be created"
        attribute_data = {
            'name': "Publication Date",
            'type': 'datetime',
            'description': "date and time of an article's publication. time component is optional and defaults to 00:00:00"
        }
        self.assertEqual(0, models.AttributeType.objects.count())        
        dirty_attr = logic.create_attribute(**attribute_data)
        self.assertEqual(1, models.AttributeType.objects.count())

    def test_attribute_correctness(self):
        "the data of a newly created attribute is what we expect"
        attribute_data = {
            'name': "Publication Date",
            'type': 'datetime',
            'description': "date and time of an article's publication. time component is optional and defaults to 00:00:00"
        }
        dirty = logic.create_attribute(**attribute_data)
        clean = models.AttributeType.objects.get(pk=dirty.id)
        for key, expected_val in attribute_data.items():
            self.assertEqual(getattr(clean, key), expected_val)

    def test_add_article_attribute(self):
        "attributes can be added to an Article. if model already has attribute, an ArticleAttribute is not created"
        # one article, no attributes exists
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(0, models.ArticleAttribute.objects.count())
        expected_key, expected_val = "title", "foo"
        logic.add_update_article_attribute(self.article, expected_key, expected_val, extant_only=False)
        
        clean_art = models.Article.objects.all()[0]
        self.assertEqual(0, models.ArticleAttribute.objects.count())
        self.assertEqual(expected_val, logic.get_attribute(clean_art, expected_key))
        
    def test_update_article_attribute(self):
        "attributes can be updated. if model already has attribute, an ArticleAttribute is not created"
        # one article, no attributes exists
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(0, models.ArticleAttribute.objects.count())
        expected_key, expected_val = "title", "foo"
        logic.add_update_article_attribute(self.article, expected_key, expected_val, extant_only=False)
        clean_art = models.Article.objects.all()[0]        
        self.assertEqual(0, models.ArticleAttribute.objects.count())
        self.assertEqual(expected_val, logic.get_attribute(clean_art, expected_key))

        expected_val = "bar"
        logic.add_update_article_attribute(clean_art, expected_key, expected_val, extant_only=False)
        clean_art = models.Article.objects.all()[0]
        self.assertEqual(0, models.ArticleAttribute.objects.count())
        self.assertEqual(expected_val, logic.get_attribute(clean_art, expected_key))

    def test_update_adhoc_attribute(self):
        "an attribute that isn't in the Article model but in the ArticleAttribute model is successfully updated"
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(0, models.ArticleAttribute.objects.count())
        expected_key, expected_val = 'foo', 'pants'
        logic.add_update_article_attribute(self.article, expected_key, expected_val, extant_only=False)
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        
        logic.add_update_article_attribute(self.article, expected_key, expected_val, extant_only=False)
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        models.ArticleAttribute.objects.get(article=self.article, key__name=expected_key, value=expected_val)


    def test_add_unknown_article_attribute(self):
        "unknown/unhandled attributes can be added to an Article"
        self.assertEqual(0, models.ArticleAttribute.objects.count())
        logic.add_update_article_attribute(self.article, "foo", "bar", extant_only=False)
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        
    def test_unknown_article_attribute_correctness(self):
        "unknown/unhandled arbitrary attributes can be added to an Article"
        dirty_attr = logic.add_update_article_attribute(self.article, "foo", "bar", extant_only=False)
        clean_attr = models.ArticleAttribute.objects.get(pk=dirty_attr.id)
        self.assertEqual(clean_attr.key.name, "foo")
        self.assertEqual(clean_attr.key.type, models.DEFAULT_ATTR_TYPE)
        self.assertEqual(clean_attr.value, "bar")

    def test_add_article_attribute_strict(self):
        "attributes cannot be added to an Article unless attribute type already exists (an update)"
        self.assertRaises(models.AttributeType.DoesNotExist, logic.add_update_article_attribute, self.article, "foo", "bar")



class ArticleAttributeInfoViaAPI(BaseCase):
    def setUp(self):
        self.c = Client()
        doc = 'elife00005.xml.json'
        article_data = json.load(open(os.path.join(self.this_dir, 'fixtures', doc), 'r'))
        self.article_obj = ingestor.import_article(logic.journal(), article_data)
        
    def tearDown(self):
        pass

    def test_get_simple_article_attribute(self):
        kwargs = {'doi': self.article_obj.doi, 'attribute': 'title'}
        url = reverse('api-get-article-attribute', kwargs=kwargs)
        expected_data = {
            'doi': self.article_obj.doi,
            'attribute': 'title',
            'attribute_value': self.article_obj.title,
            'title': self.article_obj.title,
        }
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200) # successful response
        self.assertEqual(resp.data, expected_data) # expected data

    def test_get_simple_article_attribute_case_insensitive(self):
        "doi can be case insensitive, attribute must be exact"
        kwargs = {'doi': self.article_obj.doi.upper(), 'attribute': 'title'}
        url = reverse('api-get-article-attribute', kwargs=kwargs)
        expected_data = {
            'doi': self.article_obj.doi,
            'attribute': 'title',
            'attribute_value': self.article_obj.title,
            'title': self.article_obj.title,
        }
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200) # successful response
        self.assertEqual(resp.data, expected_data) # expected data

    def test_get_article_attribute_on_non_article(self):
        kwargs = {'doi': 'foo.bar/baz', 'attribute': 'title'}
        url = reverse('api-get-article-attribute', kwargs=kwargs)
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 404)

class ArticleAttributeCreationViaAPI(BaseCase):
    def setUp(self):
        self.c = Client()
        doc = 'elife00005.xml.json'
        self.json_fixture = os.path.join(self.this_dir, 'fixtures', doc)

    def tearDown(self):
        pass

    def test_add_attribute_to_article_view(self):
        article_data = json.load(open(self.json_fixture, 'r'))
        # create the article
        dirty_article = ingestor.import_article(logic.journal(), article_data)

        expected_data = {
            'attribute': 'Article Type',
            'attribute_value': article_data['article-type'],
        }
        
        # create the expected AttributeType
        logic.create_attribute(name=expected_data['attribute'], type=models.DEFAULT_ATTR_TYPE)

        # craft the url
        kwargs = {'doi': article_data['doi']}
        url = reverse('api-add-article-attribute', kwargs=kwargs)
        resp = self.c.post(url, json.dumps(expected_data), content_type='application/json')
        
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
