import json, jsonschema
from django.core import exceptions as django_errors
from . import models, logic, fragment_logic, ajson_ingestor
from .utils import ensure, isint, lmap, subdict
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import StaticHTMLRenderer
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from .models import POA, VOR, XML2JSON
from et3.extract import path as p
from et3.render import render_item
import logging
LOG = logging.getLogger(__name__)

ERR = 'error'

def ctype(status):
    return {
        POA: 'application/vnd.elife.article-poa+json; version=2',
        VOR: 'application/vnd.elife.article-vor+json; version=2',
        ERR: 'application/json', # text/plain as well?
    }[status]

def ErrorResponse(code, title, detail=None):
    body = {'title': title, 'detail': detail}
    if not detail:
        del body['detail']

    return HttpResponse(status=code, content_type=ctype(ERR), content=json.dumps(body))

def Http404(detail=None):
    return ErrorResponse(404, "not found", detail)

def request_args(request, **overrides):
    opts = {}
    opts.update(settings.API_OPTS)
    opts.update(overrides)

    def ispositiveint(param):
        def wrap(v):
            ensure(isint(v) and int(v) > 0, "expecting positive integer for %r parameter" % param)
            return int(v)
        return wrap

    def inrange(minpp, maxpp):
        def fn(v):
            ensure(v >= minpp and v <= maxpp, "value must be between %s and %s for 'per-page' parameter" % (minpp, maxpp))
            return v
        return fn

    def asc_or_desc(val):
        v = val.strip().upper()[:4]
        ensure(v in ['ASC', 'DESC'], "expecting either 'asc' or 'desc' for 'order' parameter")
        return v

    def tobool(val):
        return val.strip().lower()[:4] == 'true'

    desc = {
        'page': [p('page', opts['page_num']), ispositiveint('page')],
        'per_page': [p('per-page', opts['per_page']), ispositiveint('per-page'), inrange(opts['min_per_page'], opts['max_per_page'])],
        'order': [p('order', opts['order_direction']), str, asc_or_desc],

        'force': [p('force', False), tobool],
        'dry_run': [p('dry-run', False), tobool]
    }
    return render_item(desc, request.GET)

#
#
#

def is_authenticated(request):
    # this header is never set, but only for this API because on /articles/42 it works
    val = request.META.get(settings.KONG_AUTH_HEADER)
    #LOG.info("authenticated? %s type %s" % (val, type(val)))
    return val or False

@api_view(['HEAD', 'GET'])
@renderer_classes((StaticHTMLRenderer,))
def ping(request):
    "returns a test response for monitoring, *never* to be cached"
    return Response('pong', content_type='text/plain; charset=UTF-8', headers={'Cache-Control': 'must-revalidate, no-cache, no-store, private'})

@api_view(['HEAD', 'GET'])
def article_list(request):
    "returns a list of snippets"
    authenticated = is_authenticated(request)
    try:
        kwargs = request_args(request)
        kwargs['only_published'] = not authenticated
        total, results = logic.latest_article_version_list(**kwargs)
        struct = {
            'total': total,
            'items': lmap(logic.article_snippet_json, results)
        }
        return Response(struct, content_type='application/vnd.elife.article-list+json; version=1')
    except AssertionError as err:
        return ErrorResponse(400, "bad request", err.message)

@api_view(['HEAD', 'GET'])
def article(request, msid):
    "return the article-json for the most recent version of the given article ID"
    authenticated = is_authenticated(request)
    try:
        av = logic.most_recent_article_version(msid, only_published=not authenticated)
        return Response(logic.article_json(av), content_type=ctype(av.status))
    except models.Article.DoesNotExist:
        return Http404()

@api_view(['HEAD', 'GET'])
def article_version_list(request, msid):
    "returns a list of versions for the given article ID"
    authenticated = is_authenticated(request)
    try:
        resp = logic.article_version_history(msid, only_published=not authenticated)
        return Response(resp, content_type='application/vnd.elife.article-history+json; version=1')
    except models.Article.DoesNotExist:
        return Http404()


@api_view(['HEAD', 'GET', 'PUT', 'POST'])
def article_version(request, msid, version):
    "returns the article-json for a specific version of the given article ID"
    authenticated = is_authenticated(request)
    try:
        # TODO: test at the HTTP level also the other requests
        av = logic.article_version(msid, version, only_published=not authenticated)
        content_type = ctype(av.status)
        method = request.method.lower()

        if method == 'head':
            # todo: test for this?
            return Response(None, content_type=content_type)

        elif method == 'get':
            pass

        elif method == 'put': # 'ingest'
            raw_data = request.POST.body # todo, DJANGO_REST might have other ways of doing things
            force, dry_run = subdict(request_args(request), ['force', 'dry_run'])
            ajson_ingestor.safe_ingest(msid, version, raw_data, force, dry_run)

        elif method == 'post': # 'publish'
            raw_data = request.PUT.body # todo: request has no PUT
            force, dry_run = subdict(request_args(request), ['force', 'dry_run'])
            ajson_ingestor.safe_publish(msid, version, raw_data, force, dry_run)

        else:
            return ErrorResponse(400, "unsupported HTTP method", "shouldn't get this far")

        content = logic.article_json(av)
        return Response(content, content_type=content_type)

    except models.ArticleVersion.DoesNotExist:
        return Http404()

    except BaseException as err:
        # unhandled
        return ErrorResponse(500, "unhandled server error", str(err))

# TODO: test 404
@api_view(['HEAD', 'GET'])
def article_related(request, msid):
    "return the related articles for a given article ID"
    authenticated = is_authenticated(request)
    try:
        rl = logic.relationships(msid, only_published=not authenticated)
        return Response(rl, content_type="application/vnd.elife.article-related+json; version=1")
    except models.Article.DoesNotExist:
        return Http404()

#
# Fragments
# not part of 'public' api
#

@api_view(['POST', 'DELETE'])
def article_fragment(request, msid, fragment_id):
    # authenticated
    if not is_authenticated(request):
        return ErrorResponse(403, "not authenticated", "only authenticated admin users can modify content")

    # article exists
    article = get_object_or_404(models.Article, manuscript_id=msid)

    try:
        reserved_keys = [XML2JSON]
        ensure(fragment_id not in reserved_keys, "that key is protected")

        if request.method == 'POST':
            fragment_logic.add_fragment_update_article(article, fragment_id, request.data)
            frag = models.ArticleFragment.objects.get(article=article, type=fragment_id)
            resp_data = frag.fragment

        elif request.method == 'DELETE':
            fragment_logic.delete_fragment_update_article(article, fragment_id)
            resp_data = {fragment_id: 'deleted'}

        return Response(resp_data)

    except django_errors.ValidationError:
        # failed model validation somehow. can happen on empty fragments
        return ErrorResponse(400, "refused: bad data", "that fragment is invalid and has been refused")

    except jsonschema.ValidationError as err:
        # client submitted json that would generate invalid article-json
        return ErrorResponse(400, "refused: bad data", "that fragment creates invalid article-json. refused: %s" % err.message)

    except AssertionError as err:
        # client broke business rules somehow
        return ErrorResponse(400, "bad request", err.message)

    except ObjectDoesNotExist:
        # article/articleversion/fragment with given ID doesn't exist
        return Http404()
