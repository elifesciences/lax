from publisher import api_v2_views
from django.test import Client
from django.urls import reverse
from django.conf import settings
from unittest import skip, mock


@skip("works by itself, but fails when called as part of test suite")
def test_VORv6_downgraded():
    "a v6 VOR compatible with v5 has it's content-type successfully downgraded"
    v6_vor = {"authorResponse": {}, "editorEvaluation": {}, "decisionLetter": {}}
    v5_ctype = api_v2_views.ctype(settings.VOR, version=5)
    v6_ctype = api_v2_views.ctype(settings.VOR, version=6)

    request_mock = api_v2_views.json_response(v6_vor, content_type=v6_ctype)
    with mock.patch("publisher.api_v2_views.article", return_value=request_mock):

        # v5 requested, we respond with a v6 ...
        resp = Client().get(
            reverse("v2:article", kwargs={"msid": 123}), HTTP_ACCEPT=v5_ctype
        )
        assert resp.status_code == 200
        assert resp.json() == v6_vor

        # that is downgraded to a v5
        assert resp.content_type == v5_ctype


@skip("works by itself, but fails when called as part of test suite")
def test_VORv6_not_downgraded():
    "a v6 VOR incompatible with v5 is not downgraded and returns a 406"
    v6_vor = {"authorResponse": {}, "editorEvaluation": {}}
    v5_ctype = api_v2_views.ctype(settings.VOR, version=5)
    v6_ctype = api_v2_views.ctype(settings.VOR, version=6)

    request_mock = api_v2_views.json_response(v6_vor, content_type=v6_ctype)
    with mock.patch("publisher.api_v2_views.article", return_value=request_mock):

        # v5 requested, we respond with a v6
        resp = Client().get(
            reverse("v2:article", kwargs={"msid": 123}), HTTP_ACCEPT=v5_ctype
        )
        assert resp.status_code == 406
