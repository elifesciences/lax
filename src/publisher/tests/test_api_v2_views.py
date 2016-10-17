import base
from os.path import join
import json
from publisher import ajson_ingestor, models
from django.test import Client
from django.core.urlresolvers import reverse
#from jsonschema import validate
#from django.conf import settings

class V2ContentTypes(base.BaseCase):
    def setUp(self):
        self.c = Client()
        self.msid = 16695
        self.ajson_fixture_v1 = join(self.fixture_dir, 'ajson', 'elife-16695-v1.xml.json') # poa
        self.ajson_fixture_v2 = join(self.fixture_dir, 'ajson', 'elife-16695-v2.xml.json') # vor

    def test_response_types(self):
        # ingest the poa and vor versions
        for path in [self.ajson_fixture_v1, self.ajson_fixture_v2]:
            ajson_ingestor.ingest_publish(json.load(open(path, 'r')))

        # map the known types to expected types
        art_list_type = 'application/vnd.elife.articles-list+json;version=1'
        art_poa_type = 'application/vnd.elife.article-poa+json;version=1'
        art_vor_type = 'application/vnd.elife.article-poa+json;version=1'
        art_history_type = 'application/vnd.elife.article-history+json;version=1'

        case_list = {
            reverse('v2:article-list'): art_list_type,
            reverse('v2:article', kwargs={'id': self.msid}): art_vor_type,
            reverse('v2:article-version-list', kwargs={'id': self.msid}): art_history_type,
            reverse('v2:article-version', kwargs={'id': self.msid, 'version': 1}): art_poa_type,
            reverse('v2:article-version', kwargs={'id': self.msid, 'version': 2}): art_vor_type,
        }

        # test
        for url, expected_type in case_list.items():
            resp = self.c.get(url)
            self.assertEqual(resp.status_code, 200,
                             "url %r failed to complete: %s" % (url, resp.status_code))
            self.assertEqual(resp.content_type, expected_type,
                             "%r failed to return %r: %s" % (url, expected_type, resp.content_type))

class V2Content(base.BaseCase):
    def setUp(self):
        ingest_these = [
            "elife.01968.json",
            "elife-16695-v1.xml.json",
            "elife-16695-v2.xml.json",
            "elife-16695-v3.xml.json"
        ]
        ajson_dir = join(self.fixture_dir, 'ajson')
        for ingestable in ingest_these:
            path = join(ajson_dir, ingestable)
            ajson_ingestor.ingest_publish(json.load(open(path, 'r')))

        self.msid1 = 1968
        self.msid2 = 16695

        self.c = Client()

    def test_article_list(self):
        "a list of articles are returned"
        resp = self.c.get(reverse('v2:article-list'))
        self.assertEqual(resp.status_code, 200)
        json_resp = json.loads(resp.content)
        self.assertEqual(len(json_resp), 2) # two results, 01968v1, 16695v3
        # TODO: assert content is valid

    def test_article(self):
        "the latest version of the requested article is returned"
        resp = self.c.get(reverse('v2:article', kwargs={'id': self.msid2}))
        self.assertEqual(resp.status_code, 200)
        # TODO: assert content is valid
        #json_resp = json.loads(resp.content)
        #json_resp['version'] == 3

    def test_article_unpublished_ver_not_returned(self):
        "unpublished article versions are not returned"
        resp = self.c.get(reverse('v2:article', kwargs={'id': self.msid2}))
        self.unpublish(self.msid2, version=3)
        self.assertEqual(resp.status_code, 200)
        # TODO: assert content is valid
        #json_resp = json.loads(resp.content)
        #json_resp['version'] == 2

    def test_article_does_not_exist(self):
        fake_msid = 123
        resp = self.c.get(reverse('v2:article', kwargs={'id': fake_msid}))
        self.assertEqual(resp.status_code, 404)

    def test_article_versions_list(self):
        "valid json content is returned "
        resp = self.c.get(reverse('v2:article-version-list', kwargs={'id': self.msid2}))
        self.assertEqual(resp.status_code, 200)
        #json_resp = json.loads(resp.content)
        #schema = json.load(open(settings.ART_HISTORY_SCHEMA, 'r'))
        # validate(json_resp, schema) # can't clone my PR for some reason ...

    def test_article_versions_list_does_not_exist(self):
        models.Article.objects.all().delete()
        self.assertEqual(models.Article.objects.count(), 0)
        resp = self.c.get(reverse('v2:article-version-list', kwargs={'id': self.msid2}))
        self.assertEqual(resp.status_code, 404)

    def test_article_version(self):
        versions = [1, 2, 3]
        for ver in versions:
            resp = self.c.get(reverse('v2:article-version', kwargs={'id': self.msid2, 'version': ver}))
            self.assertEqual(resp.status_code, 200)

    def test_article_version_art_does_not_exist(self):
        "returns 404 when an article doesn't exist for the article-version endpoint"
        models.Article.objects.all().delete()
        self.assertEqual(models.Article.objects.count(), 0)
        resp = self.c.get(reverse('v2:article-version', kwargs={'id': '123', 'version': 1}))
        self.assertEqual(resp.status_code, 404)

    def test_article_version_artver_does_not_exist(self):
        "returns 404 when a version of the article doesn't exist for the article-version endpoint"
        resp = self.c.get(reverse('v2:article-version', kwargs={'id': self.msid2, 'version': 9}))
        self.assertEqual(resp.status_code, 404)



'''
class V2PostContent(base.BaseCase):
    def setUp(self):
        ingest_these = [
            "elife.01968.json",
            "elife-16695-v1.xml.json",
            "elife-16695-v2.xml.json",
            "elife-16695-v3.xml.json"
        ]
        ajson_dir = join(self.fixture_dir, 'ajson')
        for ingestable in ingest_these:
            path = join(ajson_dir, ingestable)
            ajson_ingestor.ingest_publish(json.load(open(path, 'r')))

        self.msid1 = 1968
        self.msid2 = 16695

        self.c = Client()

    def test_add_fragment(self):
        url = reverse('v2:article-version-fragment')
        json_fragment = json.dumps({'id': self.msid1, 'pants?': 'party!'})
        q = models.ArticleFragment.get(article__manuscript_id=self.msid1)
        self.assertEqual(q.objects.count(), 1)
        # resp = self.c.post(reverse('api-create-update-article'), json_data, content_type="application/json")
        self.c.post(url, json_fragment, content_type="application/type")
        
        self.assertEqual(q.objects.count(), 2)
'''
