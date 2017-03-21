from django.conf import settings
from django.test import TestCase, Client
#from django.core.urlresolvers import reverse
from core import middleware as mware

class KongAuthMiddleware(TestCase):
    def setUp(self):
        self.c = Client()
        self.extra = {
            'REMOTE_ADDR': '10.0.2.6',
            mware.CGROUPS: 'admin',
        }

    def test_unauthenticated_request(self):
        "ensure an unauthenticated request is marked as such"
        resp = self.c.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], 'False')

    def test_authenticated_request(self):
        "ensure an authenticated request is marked as such"
        resp = self.c.get('/', **self.extra)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], 'True')

    def test_bad_authentication_request1(self):
        "client is trying to authenticate but IP doesn't originate within subnet"
        self.extra['REMOTE_ADDR'] = '192.168.0.1' # internal, but not *our* internal
        resp = self.c.get('/', **self.extra)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], 'False')

    def test_bad_authentication_request2(self):
        "client is trying to authenticate but the user group doesn't have any special permissions"
        self.extra[mware.CGROUPS] = 'user'
        resp = self.c.get('/', **self.extra)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], 'False')

    def test_bad_authentication_request3(self):
        "client is trying to authenticate but the user is unknown"
        self.extra[mware.CGROUPS] = 'party'
        resp = self.c.get('/', **self.extra)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], 'False')

class DownstreamCachine(TestCase):
    def setUp(self):
        self.c = Client()
        self.url = '/' # we could hit more urls but it's applied application-wide

    def tearDown(self):
        pass

    def test_cache_headers_in_response(self):        
        expected_headers = [
            'vary',
            'etag',
            'cache-control'
        ]
        resp = self.c.get(self.url)
        for header in expected_headers:
            self.assertTrue(resp.has_header(header), "header %r not found in response" % header)

    def test_cache_headers_not_in_response(self):
        cases = [
            'expires',
            'last-modified',
            'prama'
        ]
        resp = self.c.get(self.url)
        for header in cases:
            self.assertFalse(resp.has_header(header), "header %r present in response" % header)
