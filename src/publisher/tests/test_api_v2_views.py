import base
from os.path import join
import json
from publisher import ajson_ingestor
from django.test import Client
from django.core.urlresolvers import reverse

class V2ContentTypes(base.BaseCase):
    def setUp(self):
        self.c = Client()
        self.poa_id = 16695
        #self.vor_id = self.poa_id

        self.ajson_fixture1 = join(self.fixture_dir, 'ajson', 'elife-16695-v1.json')
        self.ajson = json.load(open(self.ajson_fixture1, 'r'))

        
    def tearDown(self):
        pass

    def test_response_types(self):
        ajson_ingestor.ingest_publish(self.ajson)
        
        art_list_type = 'application/vnd.elife.articles-list+json;version=1'
        art_poa_type = 'application/vnd.elife.article-poa+json;version=1'
        art_history_type = 'application/vnd.elife.article-history+json;version=1'
        
        case_list = {
            reverse('v2:article-list'): art_list_type,
            reverse('v2:article', kwargs={'id': self.poa_id}): art_poa_type,
            reverse('v2:article-version-list', kwargs={'id': self.poa_id}): art_history_type,
            reverse('v2:article-version', kwargs={'id': self.poa_id, 'version': 1}): art_poa_type
        }
        for url, expected_type in case_list.items():
            resp = self.c.get(url)
            self.assertEqual(resp.status_code, 200, \
                "url %r failed to complete: %s" % (url, resp.status_code))
            self.assertEqual(resp.content_type, expected_type, \
                "%r failed to return %r: %s" % (url, expected_type, resp.content_type))

class V2Content(base.BaseCase):
    def setUp(self):
        self.ajson_fixture1 = join(self.fixture_dir, 'ajson', 'elife-16695-v1.json')
        self.ajson = json.load(open(self.ajson_fixture1, 'r'))
        self.c = Client()

    def tearDown(self):
        pass

    def test_article_list(self):
        resp = self.c.get(reverse('v2:article-list'))
        self.assertEqual(resp.status_code, 200)
        expected_content_type = 'application/vnd.elife.articles-list+json;version=1'
        self.assertEqual(resp.content_type, expected_content_type)


