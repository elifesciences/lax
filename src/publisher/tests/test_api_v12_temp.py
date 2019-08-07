"""the transition from ajson v1 to ajson v2 is not going to be immediate.
requests for ajson during the transition will have their response bodies tweaked to
ensure valid content is returned depending on the version of the api requested.

* once all content is backfilled, the `middleware.upgrade` code can be removed
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
        # self.msid = 21393
        # self.status = 'poa'
        # self.ajson_fixture_api1 = join(self.fixture_dir, 'v12', 'api1', 'elife-21393-v1.xml.json') # poa, v1
        # self.ajson_fixture_api2 = join(self.fixture_dir, 'v12', 'api2', 'elife-21393-v1.xml.json') # poa, v1
        self.msid = 27134
        self.status = "vor"
        self.ajson_fixture_api1 = join(
            self.fixture_dir, "v12", "api1", "elife-27134-v2.xml.json"
        )  # vor, v2
        self.ajson_fixture_api2 = join(
            self.fixture_dir, "v12", "api2", "elife-27134-v2.xml.json"
        )  # vor, v2

        self.ajson_api1 = self.load_ajson2(self.ajson_fixture_api1)
        self.ajson_api2 = self.load_ajson2(self.ajson_fixture_api2)

        # what has a good representation of the other elements we want to target?

    def tearDown(self):
        pass

    def test_all(self):
        v1, v2, v3, v12, v123 = 1, 2, 3, 12, 123

        cases = [
            # content, request, response
            # (v1, v1, v1),
            # (v1, v2, v2),
            (v2, v1, v1),
            (v2, v2, v2),
            # (v1, v12, v2),
            (v2, v12, v2),
            # lsh@2019-08-06: introducing vor v3
            (v2, v3, v3),  # valid VOR v2 content is valid VOR v3 content
            (v3, v3, v3),
            (v3, v123, v3),
            # this test is using a valid VOR v2 fixture
            # this means we can safely 'downgrade' the response type to VOR v2
            (v3, v2, v2),
            (v3, v12, v2),
        ]

        content_idx = {
            v1: self.ajson_fixture_api1,
            v2: self.ajson_fixture_api2,
            v3: self.ajson_fixture_api2,
        }

        request_idx = {
            # the '*/*' is required, because requesting *just* v1 types will result in a 406
            v1: "application/vnd.elife.article-vor+json; version=1, */*",
            # no '*/*' required for these cases as no transformations will be happening
            v2: "application/vnd.elife.article-vor+json; version=2",
            v3: "application/vnd.elife.article-vor+json; version=3",
            v12: "application/vnd.elife.article-vor+json; version=1, application/vnd.elife.article-vor+json; version=2",
            v123: "application/vnd.elife.article-vor+json; version=1, application/vnd.elife.article-vor+json; version=2, application/vnd.elife.article-vor+json; version=3",
        }

        response_idx = {v1: self.ajson_api1, v2: self.ajson_api2, v3: self.ajson_api2}

        schema_idx = {
            v1: settings.ALL_SCHEMA_IDX[self.status][1][1],
            v2: settings.ALL_SCHEMA_IDX[self.status][0][1],
            v3: settings.ALL_SCHEMA_IDX[self.status][0][1],  # TODO: point this to v3
        }

        for ckey, rqkey, rskey in cases:
            content = content_idx[ckey]
            request = request_idx[rqkey]
            response = response_idx[rskey]

            name = " ".join(map(str, [ckey, rqkey, rskey]))
            # print(name)
            with self.subTest(name):
                try:
                    # Lax needs a v1 of an article before a v2 can be published
                    self.add_or_update_article(
                        **{
                            "manuscript_id": self.msid,
                            "version": 1,
                            "published": "2017-07-11T00:00:00Z",
                        }
                    )

                    self.publish_ajson(content)
                    actual_resp = self.c.get(
                        reverse("v2:article", kwargs={"msid": self.msid}),
                        HTTP_ACCEPT=request,
                    )
                    self.assertEqual(actual_resp.status_code, 200)
                    # response is valid
                    self.assertTrue(
                        utils.validate(actual_resp.json(), schema_idx[rskey])
                    )
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
        v1_only = "application/vnd.elife.article-poa+json; version=1"
        resp = self.c.get(
            reverse("v2:article", kwargs={"msid": self.msid}), HTTP_ACCEPT=v1_only
        )
        self.assertEqual(
            resp["warning"], "Deprecation: Support for version 1 will be removed"
        )

    def test_v2_requests_deprecation_notice_absent(self):
        v2_only = "application/vnd.elife.article-poa+json; version=2"
        resp = self.c.get(
            reverse("v2:article", kwargs={"msid": self.msid}), HTTP_ACCEPT=v2_only
        )
        self.assertFalse(resp.has_header("warning"))

    # 2018-06-26: with stricter accepts handling, this request no longer succeeds.
    # it says it only accepts v1 POA articles but will get an article-list mime type
    # def test_requests_deprecation_notice_absent_from_article_list(self):
    #    v1_only = 'application/vnd.elife.article-poa+json; version=1'
    #    resp = self.c.get(reverse('v2:article-list'), HTTP_ACCEPT=v1_only)
    #    self.assertEqual(resp['warning'], "Deprecation: Support for version 1 will be removed")

    # 2018-06-26: slightly better version
    def test_requests_deprecation_notice_absent_from_non_article_views(self):
        resp = self.c.get(reverse("v2:article", kwargs={"msid": self.msid}))
        self.assertFalse(resp.has_header("warning"))
