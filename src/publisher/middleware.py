import json
import logging
from rest_framework.response import Response as RESTResponse
from .api_v2_views import ErrorResponse
from django.http import HttpResponse
from django.http.multipartparser import parse_header

LOG = logging.getLogger(__name__)


def get_content_type(resp):
    if isinstance(resp, HttpResponse):
        # Django response object used outside of REST framework
        return resp.get("Content-Type")
    elif isinstance(resp, RESTResponse):
        return resp.content_type


def flatten_accept(header, just_elife=False):
    lst = []
    for mime in header.split(","):
        # ('application/vnd.elife.article-vor+json', {'version': 2})
        parsed_mime, parsed_params = parse_header(mime.encode())
        if just_elife and "elife" not in parsed_mime:
            continue
        # ll: ('*/*', 'version', None)
        # ll: ('application/json', 'version', None)
        # ll: ('application/vnd.elife.article-poa+json', 'version', 2)
        lst.append((parsed_mime, "version", parsed_params.pop("version", None)))
    return lst


#
#
#


def requested_version(request, response):
    """given a list of client-accepted mimes and the actual mime returned in the response,
    returns the max supported version or '*' if no version specified"""
    response_mime = flatten_accept(get_content_type(response))[0]
    bits = flatten_accept(request.META.get("HTTP_ACCEPT", "*/*"))
    versions = []
    for acceptable_mime in bits:
        if acceptable_mime[0] == response_mime[0] and acceptable_mime[-1]:
            versions.append(int(acceptable_mime[-1]))
    return (response_mime[0], "*" if not versions else max(versions))


#
# middleware
#


def error_content_check(get_response_fn):
    """REST Framework may refuse requests before we can ever handle them.
    this middleware ensures all unsuccessful responses have the correct structure"""

    def middleware(request):
        response = get_response_fn(request)
        if response.status_code > 399 and "json" in get_content_type(response):
            body = json.loads(response.content.decode("utf-8"))
            if not "title" in body and "detail" in body:
                body["title"] = body["detail"]
                del body["detail"]
                response.content = bytes(json.dumps(body, ensure_ascii=False), "utf-8")
        return response

    return middleware


def content_check(get_response_fn):
    "compares content-type in request against those that are supported."

    def middleware(request):
        request_accept_header = request.META.get("HTTP_ACCEPT", "*/*")

        # REST Framework will block unacceptable types up to a point.
        # it will not discriminate on the *value* of a parameter (like 'version')
        # this means, we can't automatically refuse version=1 of a particular mime
        # without rewriting or undermining a big chunk of their logic

        client_accepts_list = flatten_accept(request_accept_header)

        # TODO: if unsupported version requested, raise 406 immediately
        # traversing a short list must be faster than querying a database
        # if we don't check here, it will be checked in the response

        response = get_response_fn(request)
        if response.status_code != 200:
            # unsuccessful response, ignore
            return response

        # successful response
        anything = "*/*"
        response_accept_header = get_content_type(response) or anything

        # response accept header will always be a list with a single row
        response_mime = flatten_accept(response_accept_header)[0]
        response_mime_general_case = response_mime[:2] + (None,)

        anything = ("*/*", "version", None)
        almost_anything = ("application/*", "version", None)

        acceptable = (
            response_mime in client_accepts_list
            or response_mime_general_case in client_accepts_list
            or anything in client_accepts_list
            or almost_anything in client_accepts_list
        )

        # print(response_mime)
        # print(response_mime_general_case)
        # print(client_accepts_list)
        # print('acceptable?',acceptable)
        # print()

        if not acceptable:
            return ErrorResponse(
                406, "not acceptable", "could not negotiate an acceptable response type"
            )
        return response

    return middleware
