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
            mware.CGROUPS: 'user',
            mware.CID: str(uuid.uuid4()),
            mware.CUSER: 'pants'
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
