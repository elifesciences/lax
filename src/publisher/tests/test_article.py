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


class LatestArticleLogic(BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        article_data_list = [
            {'title': 'foo',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY1",
             'journal': self.journal},
             
            {'title': 'foo',
             'version': 2,
             'doi': "10.7554/eLife.DUMMY1",
             'journal': self.journal},

            {'title': 'baz',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY2",
             'journal': self.journal},

            {'title': 'baz',
             'version': 2,
             'doi': "10.7554/eLife.DUMMY2",
             'journal': self.journal},

            {'title': 'boo',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY3",
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        
    def tearDown(self):
        pass

    def test_fetch_latest(self):
        #self.assertEqual(5, models.Article.objects.count())
        self.assertEqual(3, len(list(logic.latest_articles())))

    def test_fetch_latest_limited(self):
        self.assertEqual(1, len(list(logic.latest_articles(limit=1))))

    def test_fetch_latest_where(self):
        res = list(logic.latest_articles(where=[("title = %s", "foo")]))
        self.assertEqual(1, len(res))
        self.assertEqual('foo', res[0].title)
        self.assertEqual(2, res[0].version)

    '''
    def test_fetch_latest_order(self):
        res = list(logic.latest_articles(limit=1, order_by=['title ASC']))
        self.assertEqual(1, len(res))
        self.assertEqual(2, res[0].version)
        self.assertEqual('baz', res[0].title)
    '''

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
        "an article with multiple versions is returned"
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
        "the correct article version is returned when specified via the api"
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
        resp = self.c.get(reverse("api-article-version", kwargs={'doi': doi, 'version': expected_version}))
        self.assertEqual(2, models.Article.objects.count())
        self.assertEqual(resp.data['version'], expected_version)
        self.assertEqual(resp.data['title'], 'bar')

    def test_article_info_incorrect_version(self):
        "a 404 is returned when the correct article with an incorrect version is specified via the api"
        doi = "10.7554/eLife.DUMMY"
        version = 1
        article_data_list = [
            {'title': 'foo',
             'version': version,
             'doi': doi,
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        url = reverse("api-article-version", kwargs={'doi': doi, 'version': version + 1})
        resp = self.c.get(url)
        self.assertEqual(404, resp.status_code)


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
            'name': "publication_date",
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

        new_expected_val = 'pantsPARTY'
        logic.add_update_article_attribute(self.article, expected_key, new_expected_val, extant_only=False)
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        models.ArticleAttribute.objects.get(article=self.article, key__name=expected_key, value=new_expected_val)

    def test_add_unknown_article_attribute(self):
        "unknown/unhandled attributes can be added to an Article"
        self.assertEqual(0, models.ArticleAttribute.objects.count())
        logic.add_update_article_attribute(self.article, "foo", "bar", extant_only=False)
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        
    def test_unknown_article_attribute_correctness(self):
        "unknown/unhandled arbitrary attributes can be added to an Article"
        logic.add_update_article_attribute(self.article, "foo", "bar", extant_only=False)
        clean_attr = models.ArticleAttribute.objects.all()[0]
        self.assertEqual(clean_attr.key.name, "foo")
        self.assertEqual(clean_attr.key.type, models.DEFAULT_ATTR_TYPE)
        self.assertEqual(clean_attr.value, "bar")

    def test_add_article_attribute_strict(self):
        "attributes cannot be added to an Article unless attribute type already exists (an update)"
        self.assertRaises(models.AttributeType.DoesNotExist, logic.add_update_article_attribute, self.article, "foo", "bar", extant_only=True)



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

class CreateUpdateArticleAttributeViaAPI(BaseCase):
    def setUp(self):
        self.c = Client()
        self.journal = logic.journal()
        self.article_data = [
            {'title': 'foo',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},
             
            {'title': 'bar',
             'version': 2,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal},

            {'title': 'baz',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY2",
             'journal': self.journal},
        ]
        self.articles = [logic.add_or_update_article(**article_data) for article_data in self.article_data]

    def tearDown(self):
        pass

    def test_add_attribute_to_article_view(self):
        article_data = self.article_data[0]
        attr, val = 'attribute_type', 'foo'

        # create the expected AttributeType
        logic.create_attribute(name=attr, type=models.DEFAULT_ATTR_TYPE)

        # craft the url
        kwargs = {'doi': article_data['doi']}
        url = reverse('api-add-update-article-attribute', kwargs=kwargs)
        resp = self.c.post(url, json.dumps({'attribute': attr, 'attribute_value': val}), \
                           content_type='application/json')
        
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        self.assertEqual(1, models.AttributeType.objects.count())

        expected_resp_data = {
            'key': attr,
            'value': val
        }
        # just compare a slice of the response
        resp_data_slice = utils.subdict(resp.data, expected_resp_data.keys())
        self.assertEqual(resp_data_slice, expected_resp_data)

    def test_update_attribute(self):
        "an article's attribute can be updated via the API"
        article_data = self.article_data[-1] 
        article = self.articles[-1]
        attr, val = 'attribute_type', 'pants'
        # create the attribute
        resp = logic.add_update_article_attribute(article, attr, val, extant_only=False)
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        self.assertEqual(1, models.AttributeType.objects.count())
        self.assertEqual(resp['value'], val)

        # update via the api
        kwargs = {'doi': article_data['doi']}
        url = reverse('api-add-update-article-attribute', kwargs=kwargs)
        updated_val = 'pants-party'
        payload = json.dumps({'attribute': attr, 'attribute_value': updated_val})
        resp = self.c.post(url, payload, content_type='application/json')
        
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.AttributeType.objects.count())
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        expected_resp_data = {
            'key': attr,
            'value': updated_val
        }
        # just compare a slice of the response
        resp_data_slice = utils.subdict(resp.data, expected_resp_data.keys())
        self.assertEqual(resp_data_slice, expected_resp_data)
        
    def test_update_attribute_specific_version_of_article(self):
        "the attribute of a specific version of an article can be updated via the API"
        article_data = self.article_data[0] # first version of an article with two versions
        article = self.articles[0]
        attr, val = 'attribute_type', 'pants'
        # create the attribute type and a value
        resp = logic.add_update_article_attribute(article, attr, val, extant_only=False)
        self.assertEqual(1, models.ArticleAttribute.objects.count())
        self.assertEqual(1, models.AttributeType.objects.count())
        self.assertEqual(resp['value'], val)

        # update via the api
        kwargs = {'doi': article_data['doi']}
        url = reverse('api-add-update-article-attribute', kwargs=kwargs)
        updated_val = 'pants-party'
        payload = json.dumps({'version': article_data['version'],
                              'attribute': attr,
                              'attribute_value': updated_val})
        resp = self.c.post(url, payload, content_type='application/json')
        
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, models.AttributeType.objects.count())
        self.assertEqual(1, models.ArticleAttribute.objects.count())

        expected_resp_data = {
            'key': attr,
            'value': updated_val
        }
        # just compare a slice of the response
        resp_data_slice = utils.subdict(resp.data, expected_resp_data.keys())
        self.assertEqual(resp_data_slice, expected_resp_data)

    def test_add_attribute_to_article_view_with_bad_payload(self):
        "the view should raise a 400 error if the payload cannot be deserialized from json"
        pass

    def test_add_attribute_to_article_view_with_incorrect_payload(self):
        "the view should raise a 400 error if the payload doesn't contain the values we expect"
        pass
