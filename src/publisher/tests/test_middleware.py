from publisher import api_v2_views
from django.test import Client
from django.urls import reverse
from unittest.mock import patch

# todo: bit of a placeholder test for some odd logic in the error_content_check middleware.
# it looks like it was originally written to work around some Django REST framework oddness
# but actually needs to be changed to return valid content or removed altogether.
def test_error_content_check_replaces_body():
    error_response = api_v2_views.json_response({"detail": "some error"}, code=400)
    with patch("publisher.api_v2_views.ping", return_value=error_response):
        resp = Client().get(reverse("v2:ping"))
        assert resp.content == b'{"title": "some error"}'
        assert resp.content_type == "application/json"
