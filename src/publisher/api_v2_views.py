import json, jsonschema
from django.core import exceptions as django_errors
from . import models, logic, fragment_logic
from .utils import ensure, isint, toint, lmap
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from .models import XML2JSON
from et3.extract import path as p
from et3.render import render_item
import logging
from django.http.multipartparser import parse_header

LOG = logging.getLogger(__name__)


def _ctype(content_type_key):
    "returns a content type for the given `content_type_key`."
    assert content_type_key in settings.CONTENT_TYPES
    return "application/vnd.elife.article-%s+json" % content_type_key


def ctype(content_type_key, version=None):
    """returns a content type and version header for the given `content_type_key` and `version`.
    if no `version` is specified then the latest version is used."""
    content_type = _ctype(content_type_key)
    current_version = settings.ALL_SCHEMA_IDX[content_type_key][0][0]
    version = version or current_version
    if version != current_version:
        assert version in settings.SCHEMA_VERSIONS[content_type_key]
    return "%s; version=%s" % (content_type, version)


def ErrorResponse(code, title, detail=None):
    body = {"title": title, "detail": detail}
    if not detail:
        del body["detail"]
    return HttpResponse(
        status=code, content_type="application/json", content=json.dumps(body)
    )


def Http406():
    return ErrorResponse(
        406, "not acceptable", "could not negotiate an acceptable response type"
    )


def Http404(detail=None):
    return ErrorResponse(404, "not found", detail)


def request_args(request, **overrides):
    opts = {}
    opts.update(settings.API_OPTS)
    opts.update(overrides)

    def ispositiveint(param):
        def wrap(v):
            ensure(
                isint(v) and int(v) > 0,
                "expecting positive integer for %r parameter" % param,
            )
            return int(v)

        return wrap

    def inrange(minpp, maxpp):
        def fn(v):
            ensure(
                v >= minpp and v <= maxpp,
                "value must be between %s and %s for 'per-page' parameter"
                % (minpp, maxpp),
            )
            return v

        return fn

    def asc_or_desc(val):
        v = val.strip().upper()[:4]
        ensure(
            v in ["ASC", "DESC"],
            "expecting either 'asc' or 'desc' for 'order' parameter",
        )
        return v

    desc = {
        "page": [p("page", opts["page_num"]), ispositiveint("page")],
        "per_page": [
            p("per-page", opts["per_page"]),
            ispositiveint("per-page"),
            inrange(opts["min_per_page"], opts["max_per_page"]),
        ],
        "order": [p("order", opts["order_direction"]), str, asc_or_desc],
    }
    return render_item(desc, request.GET)


def flatten_accept(accepts_header_str):
    "returns a list of triples like [(mime, 'version', version), ...]"
    lst = []
    if not accepts_header_str:
        return lst
    for mime in accepts_header_str.split(","):
        # ('application/vnd.elife.article-vor+json', {'version': 2})
        parsed_mime, parsed_params = parse_header(mime.encode())
        # ll: ('*/*', 'version', None)
        # ll: ('application/json', 'version', None)
        # ll: ('application/vnd.elife.article-poa+json', 'version', 2)
        version = parsed_params.pop("version", b"").decode("utf-8")
        lst.append((parsed_mime, "version", version or None))
    return lst


def negotiate(accepts_header_str, content_type_key):
    """parses the 'accept-type' header in the request and returns a content-type header and version.
    returns `None` if a content-type can't be negotiated.

    Note! this 'negotiation' is in addition to/overlaps with/is confused with 
    the Django REST Framework content negotiation. That library has the final word right now, unfortunately."""
    # "application/vnd.elife.article-blah+json"
    response_mime = _ctype(content_type_key)

    # 2
    max_content_type_version = settings.ALL_SCHEMA_IDX[content_type_key][0][0]

    # ("application/vnd.elife.article-blah+json", 2)
    perfect_response = (response_mime, max_content_type_version)

    if not accepts_header_str:
        # not specified/user accepts anything
        return perfect_response

    general_cases = [
        "*/*",
        "application/*",
    ]  # REST Framework says no: "application/json"
    acceptable_mimes_list = flatten_accept(accepts_header_str)
    versions = []
    for acceptable_mime in acceptable_mimes_list:
        if acceptable_mime[0] in general_cases:
            # user accepts anything
            return perfect_response

        if acceptable_mime[0] == response_mime:
            if not acceptable_mime[-1]:
                # user accepts the unqualified content type
                return perfect_response

            # user is picky about the version of the content type they want.
            # we need to make sure the version value isn't bogus.
            version = toint(acceptable_mime[-1])
            if version and version > 0 and version <= max_content_type_version:
                versions.append(version)

    if not versions:
        # can't figure out what they want
        return

    return (response_mime, max(versions))


#
#
#


def is_authenticated(request):
    # this header is never set, but only for this API because on /articles/42 it works
    val = request.META.get(settings.KONG_AUTH_HEADER)
    # LOG.info("authenticated? %s type %s" % (val, type(val)))
    return val or False


@api_view(["HEAD", "GET"])
@renderer_classes((StaticHTMLRenderer,))
def ping(request):
    "returns a test response for monitoring, *never* to be cached"
    return Response(
        "pong",
        content_type="text/plain; charset=UTF-8",
        headers={"Cache-Control": "must-revalidate, no-cache, no-store, private"},
    )


@api_view(["HEAD", "GET"])
def article_list(request):
    "returns a list of snippets"
    authenticated = is_authenticated(request)
    try:
        kwargs = request_args(request)
        kwargs["only_published"] = not authenticated
        total, results = logic.latest_article_version_list(**kwargs)
        struct = {"total": total, "items": lmap(logic.article_snippet_json, results)}
        return Response(struct, content_type=ctype(settings.LIST))
    except AssertionError as err:
        return ErrorResponse(400, "bad request", err.message)


@api_view(["HEAD", "GET"])
def article(request, msid):
    "return the article-json for the most recent version of the given article ID"
    authenticated = is_authenticated(request)
    try:
        av = logic.most_recent_article_version(msid, only_published=not authenticated)
        return Response(logic.article_json(av), content_type=ctype(av.status))
    except models.Article.DoesNotExist:
        return Http404()


def article_version_list__v1(request, msid):
    "returns a list of versions for the given article ID"
    authenticated = is_authenticated(request)
    try:
        resp = logic.article_version_history__v1(msid, only_published=not authenticated)
        return Response(resp, content_type=ctype(settings.HISTORY, 1))
    except models.Article.DoesNotExist:
        return Http404()


def article_version_list__v2(request, msid):
    "returns a list of versions for the given article ID, including preprint events."
    authenticated = is_authenticated(request)
    resp = logic.article_version_history__v2(msid, only_published=not authenticated)
    if not resp:
        return Http404()
    return Response(resp, content_type=ctype(settings.HISTORY))


@api_view(["HEAD", "GET"])
def article_version_list(request, msid):
    "returns a list of versions for the given article ID"
    accepts_header_str = request.META.get("HTTP_ACCEPT")
    content_type = negotiate(accepts_header_str, settings.HISTORY)
    if not content_type:
        return Http406()
    content_type, content_type_version = content_type
    if content_type_version == 2:
        return article_version_list__v2(request, msid)
    return article_version_list__v1(request, msid)


@api_view(["HEAD", "GET"])
def article_version(request, msid, version):
    "returns the article-json for a specific version of the given article ID"
    authenticated = is_authenticated(request)
    try:
        # TODO: test at the HTTP level also the other requests
        av = logic.article_version(msid, version, only_published=not authenticated)
        return Response(logic.article_json(av), content_type=ctype(av.status))
    except models.ArticleVersion.DoesNotExist:
        return Http404()


@api_view(["HEAD", "GET"])
def article_related(request, msid):
    "return the related articles for a given article ID"
    authenticated = is_authenticated(request)
    try:
        rl = logic.relationships(msid, only_published=not authenticated)
        return Response(rl, content_type=ctype(settings.RELATED))
    except models.Article.DoesNotExist:
        return Http404()


#
# Fragments
# not part of public api
#


@api_view(["POST", "DELETE"])
def article_fragment(request, msid, fragment_id):
    # authenticated
    if not is_authenticated(request):
        return ErrorResponse(
            403, "not authenticated", "only authenticated users can modify content",
        )

    # article exists
    article = get_object_or_404(models.Article, manuscript_id=msid)

    try:
        reserved_keys = [XML2JSON]
        ensure(fragment_id not in reserved_keys, "that key is protected")

        if request.method == "POST":
            fragment_logic.add_fragment_update_article(
                article, fragment_id, request.data
            )
            frag = models.ArticleFragment.objects.get(article=article, type=fragment_id)
            resp_data = frag.fragment

        elif request.method == "DELETE":
            fragment_logic.delete_fragment_update_article(article, fragment_id)
            resp_data = {fragment_id: "deleted"}

        return Response(resp_data)

    except django_errors.ValidationError:
        # failed model validation somehow. can happen on empty fragments
        return ErrorResponse(
            400, "refused: bad data", "that fragment is invalid and has been refused"
        )

    except jsonschema.ValidationError as err:
        # client submitted json that would generate invalid article-json
        return ErrorResponse(
            400,
            "refused: bad data",
            "that fragment creates invalid article-json. refused: %s" % err.message,
        )

    except AssertionError as err:
        # client broke business rules somehow
        return ErrorResponse(400, "bad request", err.message)

    except ObjectDoesNotExist:
        # article/articleversion/fragment with given ID doesn't exist
        return Http404()
