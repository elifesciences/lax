from publisher import api_v2_views, middleware
from django.test import Client
from django.urls import reverse
from django.conf import settings
from unittest import skip, mock


def test_all_awards_have_recipients():
    cases = [
        ({}, True),
        ({"foo": "bar"}, True),
        ({"funding": {}}, True),
        ({"funding": {"awards": []}}, True),
        # ---
        ({"funding": {"awards": [{}]}}, False),
        ({"funding": {"awards": [{"recipients": []}]}}, True),
        (
            {
                "funding": {
                    "awards": [
                        {
                            "id": "par-1",
                            "recipients": [
                                {
                                    "name": {
                                        "index": "Foo, Bar",
                                        "preferred": "Bar Foo",
                                    },
                                    "type": "Person",
                                }
                            ],
                            "source": {"name": ["Foo Society"]},
                        }
                    ]
                }
            },
            True,
        ),
    ]
    for given, expected in cases:
        assert middleware.all_awards_have_recipients(given) == expected


@skip("works by itself, but fails when called as part of test suite")
def test_content_type_downgraded():
    "content-type is downgraded for a request using a deprecated content type if content can be downgraded"
    previous_vor_type = settings.SCHEMA_VERSIONS["vor"][1]
    previous_ctype = api_v2_views.ctype(settings.VOR, version=previous_vor_type)

    ajson = {"funding": {"awards": [{"recipients": []}]}}
    request_mock = api_v2_views.json_response(ajson, content_type=previous_ctype)
    with mock.patch("publisher.api_v2_views.article", return_value=request_mock):
        # problem is probably here: the mock.patch path and reversing the path to the view function.
        resp = Client().get(
            reverse("v2:article", kwargs={"msid": 123}), HTTP_ACCEPT=previous_ctype
        )
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == previous_ctype


@skip("works by itself, but fails when called as part of test suite")
def test_content_type_not_downgraded():
    "content-type is not downgraded for a request using a deprecated content type if content cannot be downgraded"
    previous_vor_type = settings.SCHEMA_VERSIONS["vor"][1]
    previous_ctype = api_v2_views.ctype(settings.VOR, version=previous_vor_type)

    ajson = {"funding": {"awards": [{}]}}
    request_mock = api_v2_views.json_response(ajson, content_type=previous_ctype)
    with mock.patch("publisher.api_v2_views.article", return_value=request_mock):
        resp = Client().get(
            reverse("v2:article", kwargs={"msid": 123}), HTTP_ACCEPT=previous_ctype
        )
        assert resp.status_code == 406
