from publisher import api_v2_views
from django.test import Client
from django.urls import reverse
from unittest import skip, mock

# todo: bit of a placeholder test for some odd logic in the error_content_check middleware.
# it looks like it was originally written to work around some Django REST framework oddness
# but actually needs to be changed to return valid content or removed altogether.
@skip("works by itself, but fails when called as part of test suite")
def test_error_content_check_replaces_body():
    with mock.patch("publisher.api_v2_views.ping") as m:
        error_response = api_v2_views.json_response({"detail": "some error"}, code=400)
        m.return_value = error_response
        resp = Client().get(reverse("v2:ping"))
        assert resp.content == b'{"title": "some error"}'
        assert resp.content_type == "application/json"
