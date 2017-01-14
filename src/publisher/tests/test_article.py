from publisher import models, logic
from publisher import api_v1_views as views
from .base import BaseCase
import logging
from datetime import datetime, timedelta
from django.test import Client
from django.core.urlresolvers import reverse

logging.getLogger("").setLevel(logging.WARNING) # suppresses debug, info messages

class ArticleLogic(BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        self.article_data = {
            'title': "Molecular architecture of human polycomb repressive complex 2",
            'version': 1,
            'doi': "10.7554/eLife.00005",
            'journal': self.journal,
        }

    def tearDown(self):
        pass

    def test_fetch_nonexistant_article(self):
        self.assertEqual(0, models.Article.objects.count())
        self.assertRaises(models.Article.DoesNotExist, logic.article, 'paaaaaaaaan/t.s')
        self.assertEqual(0, models.Article.objects.count())

    def test_fetches_latest_always(self):
        "when version is not specified, `logic.article` returns the latest"
        self.assertEqual(0, models.Article.objects.count())
        doi = "10.7554/eLife.01234"
        now = datetime.now()
        one_ago = now - timedelta(days=1)
        two_ago = now - timedelta(days=2)
        three_ago = now - timedelta(days=3)
        article_data_list = [
            {'title': 'foo',
             'version': 1,
             'doi': doi,
             'pub-date': three_ago,
             'journal': self.journal},

            {'title': 'bar',
             'version': 2,
             'doi': doi,
             'update': two_ago,
             'journal': self.journal},

            {'title': 'baz',
             'version': 3,
             'doi': doi,
             'update': one_ago,
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(3, models.ArticleVersion.objects.count())

        art, ver = logic.article(doi)
        self.assertEqual(ver.version, 3)
        self.assertEqual(ver.title, 'baz')

class ArticleInfoViaApi(BaseCase):
    def setUp(self):
        self.c = Client()
        self.journal = logic.journal()
        self.article_data = {
            'title': "Molecular architecture of human polycomb repressive complex 2",
            'version': 1,
            'status': 'poa',
            'doi': "10.7554/eLife.00005",
            'pub-date': '2000-01-01',
            'journal': self.journal,
        }

    def tearDown(self):
        pass

    def test_article_info_api(self):
        "article data returned by the api is the same as what is serialize"
        article, version = logic.add_or_update_article(**self.article_data)
        resp = self.c.get(reverse("api-article", kwargs={'doi': article.doi}))
        expected = views.ArticleVersionSerializer(version).data
        actual = resp.data
        self.assertEqual(actual, expected)

    def test_article_info_api_no_article(self):
        "non existant articles raise a 404"
        doi = 'paaaaaaaaan/t.s'
        resp = self.c.get(reverse("api-article", kwargs={'doi': doi}))
        self.assertEqual(resp.status_code, 404)

    def test_article_info_api_case_insensitive(self):
        "article data returned by the api is the same as what is serialize"
        kwargs = self.article_data
        kwargs['doi'] = kwargs['doi'].upper()
        article, version = logic.add_or_update_article(**kwargs)
        resp = self.c.get(reverse("api-article", kwargs={'doi': article.doi}))
        self.assertEqual(resp.data, views.ArticleVersionSerializer(version).data)

    def test_article_info_version_grouping_no_art(self):
        doi = 'paaaaaaaaan/t.s'
        resp = self.c.get(reverse("api-article-versions", kwargs={'doi': doi}))
        self.assertEqual(404, resp.status_code)

    def test_article_info_version_grouping(self):
        "an article with multiple versions is returned"
        doi = "10.7554/eLife.01234"
        now = datetime.now()
        one_ago = now - timedelta(days=1)
        two_ago = now - timedelta(days=2)
        three_ago = now - timedelta(days=3)
        article_data_list = [
            {'title': 'foo',
             'version': 1,
             'doi': doi,
             'pub-date': three_ago,
             'journal': self.journal},

            {'title': 'bar',
             'version': 2,
             'doi': doi,
             'update': two_ago,
             'journal': self.journal},

            {'title': 'baz',
             'version': 3,
             'doi': doi,
             'update': one_ago,
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]

        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(3, models.ArticleVersion.objects.count())

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
        doi = "10.7554/eLife.01234"
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
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(2, models.ArticleVersion.objects.count())

        expected_version = 1
        api_args = {'doi': doi, 'version': expected_version}
        resp = self.c.get(reverse("api-article-version", kwargs=api_args))

        self.assertEqual(resp.data['version'], expected_version)
        self.assertEqual(resp.data['title'], 'bar')

    def test_article_info_incorrect_version(self):
        "a 404 is returned when the correct article with an incorrect version is specified via the api"
        doi = "10.7554/eLife.01234"
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

    '''
    def test_article_corpus_api(self):
        self.assertEqual(0, models.Article.objects.count())
        resp = self.c.get(reverse("api-corpus-info"))
        self.assertEqual(resp.data, {'article-count': 0,
                                     'research-article-count': 0})
        article, version = logic.add_or_update_article(**self.article_data)
        self.assertEqual(1, models.Article.objects.count())
        resp = self.c.get(reverse("api-corpus-info"))
        self.assertEqual(resp.data, {'article-count': 1,
                                     'research-article-count': 0})
    '''
