import base
from django.test import Client
from django.core.urlresolvers import reverse

class TestV2Urls(base.BaseCase):
    def setUp(self):
        self.c = Client()
        self.poa_id = '16950'
        self.vor_id = self.poa_id

    def tearDown(self):
        pass

    def test_article_list(self):
        resp = self.c.get(reverse('v2:article-list'))
        self.assertEqual(resp.status_code, 200)
        expected_cc = 'application/vnd.elife.articles-list+json;version=1'
        self.assertEqual(resp.content_type, expected_cc)

    def test_article(self):
        resp = self.c.get(reverse('v2:article', kwargs={'id': self.poa_id}))
        self.assertEqual(resp.status_code, 200)
        expected_content_type = 'application/vnd.elife.article-poa+json;version=1'
        self.assertEqual(resp.content_type, expected_content_type)

    def test_article_version_list(self):
        resp = self.c.get(reverse('v2:article-version-list', kwargs={'id': self.poa_id}))
        self.assertEqual(resp.status_code, 200)
        expected_content_type = 'application/vnd.elife.article-history+json;version=1'
        self.assertEqual(resp.content_type, expected_content_type)

    def test_article_version(self):
        resp = self.c.get(reverse('v2:article-version', kwargs={'id': self.poa_id, 'version': 1}))
        self.assertEqual(resp.status_code, 200)
        expected_content_type = 'application/vnd.elife.article-poa+json;version=1'
        self.assertEqual(resp.content_type, expected_content_type)
