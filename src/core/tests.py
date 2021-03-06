from django.conf import settings
from django.test import TestCase, Client, override_settings
from core import middleware as mware


class KongAuthMiddleware(TestCase):
    def setUp(self):
        self.c = Client()

    def test_unauthenticated_request(self):
        "ensure an unauthenticated request is marked as such"
        resp = self.c.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], "False")

    def test_authenticated_request(self):
        "ensure an authenticated request is marked as such"
        resp = self.c.get("/", **{mware.CGROUPS: "view-unpublished-content"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], "True")

    def test_authenticated_request_multiple_groups(self):
        "ensure an authenticated request is marked as such"
        resp = self.c.get("/", **{mware.CGROUPS: "user, view-unpublished-content"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], "True")

    def test_bad_authentication_request2(self):
        "client is trying to authenticate but the user group doesn't have any special permissions"
        resp = self.c.get("/", **{mware.CGROUPS: "user"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], "False")

    def test_bad_authentication_request3(self):
        "client is trying to authenticate but the user is unknown"
        resp = self.c.get("/", **{mware.CGROUPS: "party"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], "False")


class DownstreamCaching(TestCase):
    def setUp(self):
        self.c = Client()
        self.url = "/"  # we could hit more urls but it's applied application-wide

    def tearDown(self):
        pass

    def test_cache_headers_in_response(self):
        expected_headers = ["vary", "etag", "cache-control"]
        resp = self.c.get(self.url)
        for header in expected_headers:
            self.assertTrue(
                resp.has_header(header), "header %r not found in response" % header
            )

    def test_cache_headers_not_in_response(self):
        cases = ["expires", "last-modified", "prama"]
        resp = self.c.get(self.url)
        for header in cases:
            self.assertFalse(
                resp.has_header(header), "header %r present in response" % header
            )

    def test_error_responses_are_not_cached(self):
        resp = self.c.get("/does-not-exist")
        for expected in ["no-store", "must-revalidate", "no-cache"]:
            self.assertTrue(expected in resp["Cache-Control"])

    @override_settings(CACHE_HEADERS_TTL=30)
    def test_custom_ttl_in_configuration(self):
        resp = self.c.get(self.url)
        cache_control = self._parse_cache_control(resp)
        self.assertIn("max-age=30", cache_control)
        self.assertIn("stale-while-revalidate=30", cache_control)

    def _parse_cache_control(self, resp):
        return [
            directive.strip() for directive in resp.get("Cache-Control", "").split(",")
        ]
