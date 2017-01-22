from .base import BaseCase
from django.test import Client
from django.core.urlresolvers import reverse

class TestViews(BaseCase):
    def setUp(self):
        self.c = Client()

    def tearDown(self):
        pass

    def test_landing_view(self):
        resp = self.c.get(reverse('pub-landing'))
        self.assertEqual(resp.status_code, 200)
