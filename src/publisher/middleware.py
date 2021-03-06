from django.conf import settings
import json
import logging
from .utils import isint
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


def has_structured_abstract(ajson):
    "returns True if ajson contains a structured abstract"
    if "abstract" in ajson:
        # a regular abstract has the keys 'type' and 'text'
        # a structured abstract has the keys 'type', 'id', 'title', 'content'
        # a structured abstract will *not* have the 'text' key
        return "text" not in ajson["abstract"]["content"][0]


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


# deprecated content-types are simply the oldest ones

DEPRECATED_VOR = (
    "application/vnd.elife.article-vor+json",
    "version",
    bytes(str(settings.ALL_SCHEMA_IDX["vor"][-1][0]), "utf-8"),
)
DEPRECATED_POA = (
    "application/vnd.elife.article-poa+json",
    "version",
    bytes(str(settings.ALL_SCHEMA_IDX["poa"][-1][0]), "utf-8"),
)

DEPRECATED_CONTENT_TYPES = [DEPRECATED_VOR, DEPRECATED_POA]


def is_deprecated(request):
    accepts = flatten_accept(request.META.get("HTTP_ACCEPT", "*/*"))
    for target in DEPRECATED_CONTENT_TYPES:
        if target in accepts:
            return True


#
# middleware
#


def deprecated(get_response_fn):
    def middleware(request):
        response = get_response_fn(request)
        if is_deprecated(request):
            msg = "Deprecation: Support for this Content-Type version will be removed"
            response["warning"] = msg
        return response

    return middleware


#
#
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


#
# downgrade VOR
# when a content-type less than the current VOR version is requested,
# downgrade response content-type if possible
#


def vor_valid_under_v3(ajson):
    "returns True if given article-json is valid under version 3 of the VOR spec (no structured abstract)"
    return not has_structured_abstract(ajson)


def downgrade_vor_content_type(get_response_fn):
    """if a content-type less than the current VOR version is requested, downgrade content-type if possible 
    or return a 406"""

    def middleware(request):
        request_accept_header = request.META.get("HTTP_ACCEPT", "*/*")
        response = get_response_fn(request)

        if response.status_code != 200:
            # unsuccessful response, ignore
            return response

        # are we returning VOR content?
        vor_ctype = "application/vnd.elife.article-vor+json"
        resp_ctype = get_content_type(response)

        if vor_ctype not in resp_ctype:
            # this isn't a vor
            return response

        client_accepts_list = flatten_accept(request_accept_header)
        client_accepts_vor_list = [
            row for row in client_accepts_list if row[0] == vor_ctype
        ]

        # [1, 2, 3, ...]
        client_accepts_vor_versions = [
            int(row[-1]) for row in client_accepts_vor_list if isint(row[-1])
        ]

        if not client_accepts_vor_versions:
            # no specific version specified, return latest version
            return response

        max_accepted_vor = max(client_accepts_vor_versions)
        current_vor_version = settings.ALL_SCHEMA_IDX["vor"][0][0]

        if max_accepted_vor == current_vor_version:
            # user requested the current latest VOR version
            return response

        body = json.loads(response.content.decode("utf-8"))

        if max_accepted_vor == 3:
            # client specifically accepts a v3 VOR only
            # we might be ok if the content is valid under v3
            if vor_valid_under_v3(body):
                # all good, drop content-type returned to VOR v3
                # we have to recreate the response because the Django/REST library response is immutable or something
                new_content_type = "application/vnd.elife.article-vor+json; version=3"
                new_response = HttpResponse(
                    response.content, content_type=new_content_type
                )
                # this is where RESTResponses keep it
                new_response.content_type = new_content_type
                return new_response

        # an unsupported VOR version was requested.
        return ErrorResponse(
            406, "not acceptable", "could not negotiate an acceptable response type",
        )

    return middleware


def poa_valid_under_v2(ajson):
    "returns True if the given article-json is valid POA v2 (no structured abstract)"
    return not has_structured_abstract(ajson)


def downgrade_poa_content_type(get_response_fn):
    """if a content-type less than the current VOR version is requested, downgrade content-type if possible or return a 406"""

    def middleware(request):
        request_accept_header = request.META.get("HTTP_ACCEPT", "*/*")
        response = get_response_fn(request)

        if response.status_code != 200:
            # unsuccessful response, ignore
            return response

        # are we returning POA content?
        poa_ctype = "application/vnd.elife.article-poa+json"
        resp_ctype = get_content_type(response)

        if poa_ctype not in resp_ctype:
            # this isn't a poa
            return response

        client_accepts_list = flatten_accept(request_accept_header)
        client_accepts_poa_list = [
            row for row in client_accepts_list if row[0] == poa_ctype
        ]

        # [1, 2, 3, ...]
        client_accepts_poa_versions = [
            int(row[-1]) for row in client_accepts_poa_list if isint(row[-1])
        ]

        if not client_accepts_poa_versions:
            # no specific version specified, return latest version
            return response

        max_accepted_poa = max(client_accepts_poa_versions)
        current_poa_version = settings.ALL_SCHEMA_IDX["poa"][0][0]

        if max_accepted_poa == current_poa_version:
            # user requested the current latest POA version
            return response

        if max_accepted_poa == 2:
            # client specifically accepts a v2 POA only (deprecated)
            # we might be ok if the content is valid under v3 and v2
            body = json.loads(response.content.decode("utf-8"))
            if poa_valid_under_v2(body):
                # all good, drop content-type returned to POA v2
                # we have to recreate the response because the Django/REST library response is immutable or something
                new_content_type = "application/vnd.elife.article-poa+json; version=2"
                new_response = HttpResponse(
                    response.content, content_type=new_content_type
                )
                # this is where RESTResponses keep it
                new_response.content_type = new_content_type
                return new_response

        # an unsupported POA version was requested
        return ErrorResponse(
            406, "not acceptable", "could not negotiate an acceptable response type",
        )

    return middleware
