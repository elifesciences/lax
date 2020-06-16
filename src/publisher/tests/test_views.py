from django.test import Client
from django.core.urlresolvers import reverse


def test_landing_view():
    resp = Client().get(reverse("pub-landing"))
    assert resp.status_code == 200
