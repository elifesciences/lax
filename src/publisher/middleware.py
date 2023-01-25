from django.conf import settings
import json
import logging
from .utils import isint
from .api_v2_views import flatten_accept, _ctype, http_406

LOG = logging.getLogger(__name__)


def get_content_type(resp):
    # `resp.content_type` would also work, *however* we can't guarantee
    # every HttpResponse object will subclass our custom response.
    return resp.get("Content-Type")


def has_structured_abstract(ajson):
    "returns `True` if `ajson` contains a structured abstract"
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

# a list of triples like `(mime, 'version', version)`
# see `flatten_accept`
DEPRECATED_CONTENT_TYPES = []
for tpe, rows in settings.ALL_SCHEMA_IDX.items():
    if len(rows) > 1:
        for deprecated_version, _ in rows[1:]:
            # stringify version because that is what `flatten_accept` returns
            deprecated = (_ctype(tpe), "version", str(deprecated_version))
            DEPRECATED_CONTENT_TYPES.append(deprecated)


def is_deprecated(accepts_header_str):
    "returns `True` if *any* of the mime types in the parsed 'accepts' header string are deprecated."
    accepts = flatten_accept(accepts_header_str)
    for target in DEPRECATED_CONTENT_TYPES:
        if target in accepts:
            return True


#
# middleware
#


def mark_deprecated(get_response_fn):
    """returns `True` if *any* of the *requested* content types are deprecated.
    lsh@2021-07-6: should probably be changed to test the negotiated content type."""

    def middleware(request):
        accepts_header_str = request.META.get("HTTP_ACCEPT", "*/*")
        response = get_response_fn(request)
        if is_deprecated(accepts_header_str):
            msg = "Deprecation: Support for this Content-Type version will be removed"
            response["warning"] = msg
        return response

    return middleware


#
#
#


# todo: this middleware needs to go away and `error_response` in api_v2_views needs to
# emit responses valid against https://datatracker.ietf.org/doc/html/rfc7807 and
# https://github.com/elifesciences/api-raml/blob/develop/dist/model/error.v1.json
def error_content_check(get_response_fn):
    """This middleware ensures all unsuccessful responses have the correct structure."""

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
            return http_406()
        return response

    return middleware


#
# downgrade VOR
# when a content-type less than the current VOR version is requested,
# downgrade response content-type if possible
#


def vor_valid_under_v6(ajson):
    "returns True if given article-json is valid under version 6 of the VOR spec."
    # TODO: pending outcome of https://github.com/elifesciences/api-raml/pull/292
    return True


def downgrade_vor_content_type(get_response_fn):
    """if a content-type less than the current VOR version is requested,
    downgrade content-type if possible or return a 406"""

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

        if max_accepted_vor == 6:
            # client specifically accepts a v6 VOR only (deprecated)
            # we might be ok if the content is valid under v6
            if vor_valid_under_v6(body):
                # all good, drop content-type returned to VOR v6
                new_content_type = "application/vnd.elife.article-vor+json; version=6"
                response["Content-Type"] = new_content_type
                return response

        # an unsupported VOR version was requested.
        return http_406()

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
                new_content_type = "application/vnd.elife.article-poa+json; version=2"
                response["Content-Type"] = new_content_type
                return response

        # an unsupported POA version was requested
        return http_406()

    return middleware
