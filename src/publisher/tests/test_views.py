from django.test import Client
from django.urls import reverse


def test_landing_view():
    resp = Client().get(reverse("pub-landing"))
    assert resp.status_code == 200
