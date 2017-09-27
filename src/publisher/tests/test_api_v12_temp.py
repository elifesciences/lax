"""the transition from ajson v1 to ajson v2 is not going to be immediate.
requests for ajson during the transition will have their response bodies tweaked to
ensure valid content is returned depending on the version of the api requested.

* once all content is backfilled, the middleware.upgrade code can be removed
* once the deprecation period ends, the middleware can be removed entirely

"""

#from unittest import skip
#from core import middleware as mware
#from datetime import timedelta
from . import base
from os.path import join
#import json
from publisher import logic, models, utils
from django.test import Client  # , override_settings
from django.core.urlresolvers import reverse
from django.conf import settings
#from unittest.mock import patch, Mock

class One(base.BaseCase):
    def setUp(self):
        self.c = Client()

        # additionalFiles
        self.msid = 21393
        self.ajson_fixture_api1 = join(self.fixture_dir, 'v12', 'api1', 'elife-21393-v1.xml.json') # poa, v1 ajson
        self.ajson_fixture_api2 = join(self.fixture_dir, 'v12', 'api2', 'elife-21393-v1.xml.json') # poa, v1 ajson

        self.ajson_api1 = self.load_ajson2(self.ajson_fixture_api1)
        self.ajson_api2 = self.load_ajson2(self.ajson_fixture_api2)

        # what has a good representation of the other elements we want to target?

    def tearDown(self):
        pass

    def test_v1_requests_on_v1_content__additionalFiles(self):
        "v1 requests on v1 content continue to validate. checks articles with additionalFiles content"
        self.publish_ajson(self.ajson_fixture_api1)
        av = models.ArticleVersion.objects.all()[0]

        v1_only = 'application/vnd.elife.article-poa+json; version=1'
        resp = self.c.get(reverse('v2:article', kwargs={'id': self.msid}), HTTP_ACCEPT=v1_only)
        self.assertEqual(resp.status_code, 200)

        # ensure nothing has changed in the request
        self.assertEqual(resp.json(), logic.article_json(av))

    def test_v1_requests_on_v1_content__everythingelse(self):
        "v1 requests on v1 content continue to validate. checks articles with figures"
        # need a fixture with figures
        self.fail()

    def test_v1_requests_on_v2_content(self):
        "v1 requests on v2 content downgrade correctly and validate"
        self.publish_ajson(self.ajson_fixture_api2)

        v1_only = 'application/vnd.elife.article-poa+json; version=1'
        resp = self.c.get(reverse('v2:article', kwargs={'id': self.msid}), HTTP_ACCEPT=v1_only)
        self.assertEqual(resp.status_code, 200)

        # v2 content has been downgraded to be the same as v1 content
        self.assertEqual(self.load_ajson2(resp.json()), self.ajson_api1)

        # downgraded v2 content validates under v1
        self.assertTrue(utils.validate(resp.json(), settings.ALL_SCHEMA_IDX['poa'][1][1]))

    def test_v2_requests_on_v1_content(self):
        "v2 requests on v1 content upgrade correctly and validate"
        self.publish_ajson(self.ajson_fixture_api1)

        v2_only = 'application/vnd.elife.article-vor+json; version=2'
        resp = self.c.get(reverse('v2:article', kwargs={'id': self.msid}), HTTP_ACCEPT=v2_only)
        self.assertEqual(resp.status_code, 200)

        # specific changes have been made ...
        self.assertTrue('label' in resp.json()['additionalFiles'][0])
        # test anything that identifies as a 'figure'

    def test_v2_requests_on_v2_content(self):
        "v2 requests on v2 content continue to validate"
        self.fail()

    def test_multiple_versions_supported_on_v1_content(self):
        "requests that support both v1 and v2 content will return v2 content"
        # interesting case when specifying multiple supported versions. what do we do here?
        # because lax will detect the v2 request and upgrade if necessary
        # many = 'application/vnd.elife.article-poa+json; version=1, application/vnd.elife.article-vor+json; version=2'
        self.fail()

    def test_multiple_versions_supported_on_v2_content(self):
        "requests that support both v1 and v2 content will return v2 content"
        # interesting case when specifying multiple supported versions. what do we do here?
        # because lax will detect the v2 request and upgrade if necessary
        # many = 'application/vnd.elife.article-poa+json; version=1, application/vnd.elife.article-vor+json; version=2'
        self.fail()

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
