import uuid
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
            mware.CID: str(uuid.uuid4()),
            mware.CUSER: 'pants'
        }

    def test_unauthenticated_request(self):
        "ensure an unauthenticated request is marked as such"
        resp = self.c.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp[settings.KONG_AUTH_HEADER], 'False')

    def test_anonymous_request(self):
        "client is trying to authenticate but the user is 'anonymous'"
        self.extra[mware.CUSER] = 'anonymous'
        resp = self.c.get('/', **self.extra)
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
