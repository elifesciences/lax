"""the transition from ajson v1 to ajson v2 is not going to be immediate.
requests for ajson during the transition will have their response bodies tweaked to
ensure valid content is returned depending on the version of the api requested.

* once all content is backfilled, the middleware.upgrade code can be removed
* once the deprecation period ends, the middleware can be removed entirely

"""

from . import base
from os.path import join
from publisher import models, utils
from django.test import Client  # , override_settings
from django.core.urlresolvers import reverse
from django.conf import settings

class One(base.BaseCase):
    def setUp(self):
        self.c = Client()

        # additionalFiles
        #self.msid = 21393
        #self.status = 'poa'
        # self.ajson_fixture_api1 = join(self.fixture_dir, 'v12', 'api1', 'elife-21393-v1.xml.json') # poa, v1
        # self.ajson_fixture_api2 = join(self.fixture_dir, 'v12', 'api2', 'elife-21393-v1.xml.json') # poa, v1
        self.msid = 27134
        self.status = 'vor'
        self.ajson_fixture_api1 = join(self.fixture_dir, 'v12', 'api1', 'elife-27134-v2.xml.json') # vor, v2
        self.ajson_fixture_api2 = join(self.fixture_dir, 'v12', 'api2', 'elife-27134-v2.xml.json') # vor, v2

        self.ajson_api1 = self.load_ajson2(self.ajson_fixture_api1)
        self.ajson_api2 = self.load_ajson2(self.ajson_fixture_api2)

        # what has a good representation of the other elements we want to target?

    def tearDown(self):
        pass

    def test_all(self):
        v1, v2, v12 = 1, 2, 12

        cases = [
            # content, request, response
            #(v1, v1, v1),
            #(v1, v2, v2),

            (v2, v1, v1),
            (v2, v2, v2),

            #(v1, v12, v2),
            (v2, v12, v2),
        ]

        content_idx = {
            v1: self.ajson_fixture_api1,
            v2: self.ajson_fixture_api2
        }

        request_idx = {
            v1: 'application/vnd.elife.article-poa+json; version=1',
            v2: 'application/vnd.elife.article-poa+json; version=2',
            v12: 'application/vnd.elife.article-poa+json; version=1, application/vnd.elife.article-poa+json; version=2',
        }

        response_idx = {
            v1: self.ajson_api1,
            v2: self.ajson_api2
        }

        schema_idx = {
            v1: settings.ALL_SCHEMA_IDX[self.status][1][1],
            v2: settings.ALL_SCHEMA_IDX[self.status][0][1],
        }

        for ckey, rqkey, rskey in cases:
            content = content_idx[ckey]
            request = request_idx[rqkey]
            response = response_idx[rskey]

            name = ' '.join(map(str, [ckey, rqkey, rskey]))
            # print(name)
            with self.subTest(name):
                try:
                    # Lax needs a v1 before a v2 can be published
                    self.add_or_update_article(**{
                        'manuscript_id': self.msid,
                        'version': 1,
                        'published': '2017-07-11T00:00:00Z'
                    })

                    self.publish_ajson(content)
                    actual_resp = self.c.get(reverse('v2:article', kwargs={'id': self.msid}), HTTP_ACCEPT=request)
                    self.assertEqual(actual_resp.status_code, 200)
                    # response is valid
                    self.assertTrue(utils.validate(actual_resp.json(), schema_idx[rskey]))
                    # response is equal to what we're expecting
                    actual_json = self.load_ajson2(actual_resp.json())
                    # slightly more isolated error messages
                    self.assertEqual(actual_json.keys(), response.keys())
                    for key in response.keys():
                        self.assertEqual(actual_json.get(key), response.get(key))

                finally:
                    models.Article.objects.all().delete()

    # deprecation notice

    def test_v1_requests_deprecation_notice_present(self):
        v1_only = 'application/vnd.elife.article-poa+json; version=1'
        resp = self.c.get(reverse('v2:article', kwargs={'id': self.msid}), HTTP_ACCEPT=v1_only)
        self.assertEqual(resp['warning'], "Deprecation: Support for version 1 will be removed")

    def test_v2_requests_deprecation_notice_absent(self):
        v2_only = 'application/vnd.elife.article-poa+json; version=2'
        resp = self.c.get(reverse('v2:article', kwargs={'id': self.msid}), HTTP_ACCEPT=v2_only)
        self.assertFalse(resp.has_header('warning'))

    def test_requests_deprecation_notice_absent(self):
        v1_only = 'application/vnd.elife.article-poa+json; version=1'
        resp = self.c.get(reverse('v2:article-list'), HTTP_ACCEPT=v1_only)
        self.assertEqual(resp['warning'], "Deprecation: Support for version 1 will be removed")
