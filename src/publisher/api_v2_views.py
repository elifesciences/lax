from jsonschema import ValidationError
from django.db import transaction
from . import models, logic, fragment_logic
from .utils import ensure, isint
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import Http404
from django.conf import settings
from .models import POA, XML2JSON
from et3.extract import path as p
from et3.render import render_item

import logging
LOG = logging.getLogger(__name__)

def ctype(status):
    poa_ctype = 'application/vnd.elife.article-poa+json;version=1'
    vor_ctype = 'application/vnd.elife.article-vor+json;version=1'
    return poa_ctype if status == POA else vor_ctype

def request_args(request, **overrides):
    opts = {}
    opts.update(settings.API_OPTS)
    opts.update(overrides)

    def ispositiveint(v):
        ensure(isint(v) and int(v) > 0, "expecting positive integer, got: %s" % v)
        return int(v)

    def inrange(minpp, maxpp):
        def fn(v):
            ensure(v >= minpp and v <= maxpp, "value must be between %s and %s" % (minpp, maxpp))
            return v
        return fn

    def asc_or_desc(val):
        v = val.strip().upper()
        ensure(v in ['ASC', 'DESC'], "expecting either 'asc' or 'desc' for 'order' parameter, got: %s" % val)
        return v

    desc = {
        'page': [p('page', opts['page_num']), ispositiveint],
        'per_page': [p('per-page', opts['per_page']), ispositiveint, inrange(opts['min_per_page'], opts['max_per_page'])],
        'order': [p('order', opts['order_direction']), str, asc_or_desc]
    }
    return render_item(desc, request.GET)

#
#
#

def is_authenticated(request):
    val = request.META.get(settings.KONG_AUTH_HEADER)
    #LOG.info("authenticated? %s type %s" % (val, type(val)))
    return val or False

@api_view(['GET'])
def article_list(request):
    "returns a list of snippets"
    authenticated = is_authenticated(request)
    try:
        kwargs = request_args(request)
        kwargs['only_published'] = not authenticated
        results = logic.latest_article_versions(**kwargs)
        struct = {
            'total': len(results), # TODO: probably wrong now.
            'items': map(logic.article_snippet_json, results),
        }
        return Response(struct, content_type='application/vnd.elife.article-list+json;version=1')
    except AssertionError as err:
        return Response(err.message, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def article(request, id):
    "return the article-json for the most recent version of the given article ID"
    authenticated = is_authenticated(request)
    try:
        av = logic.most_recent_article_version(id, only_published=not authenticated)
        return Response(logic.article_json(av), content_type=ctype(av.status))
    except models.Article.DoesNotExist:
        raise Http404()

@api_view(['GET'])
def article_version_list(request, id):
    "returns a list of versions for the given article ID"
    authenticated = is_authenticated(request)
    try:
        resp = logic.article_version_history(id, only_published=not authenticated)
        return Response(resp, content_type='application/vnd.elife.article-history+json;version=1')
    except models.Article.DoesNotExist:
        raise Http404()

@api_view(['GET'])
def article_version(request, id, version):
    "returns the article-json for a specific version of the given article ID"
    authenticated = is_authenticated(request)
    try:
        av = logic.article_version(id, version, only_published=authenticated)
        return Response(logic.article_json(av), content_type=ctype(av.status))
    except models.ArticleVersion.DoesNotExist:
        raise Http404()

#
# not part of public api
#

@api_view(['POST'])
def article_fragment(request, art_id, fragment_id):
    only_published = is_authenticated(request)
    try:
        reserved_keys = [XML2JSON]
        ensure(fragment_id not in reserved_keys, "that key is taken")
        with transaction.atomic():
            av = logic.most_recent_article_version(art_id, only_published)
            data = request.data
            frag, created, updated = fragment_logic.add(av.article, fragment_id, data, update=True)
            ensure(created or updated, "fragment was not created/updated")
            fragment_logic.merge_if_valid(av, quiet=False)
            return Response(frag.fragment) # return the data they gave us

    except ValidationError as err:
        # client submitted json that would generate invalid article-json
        return Response("that fragment creates invalid article-json. refused: %s" % err.message, status=400)

    except AssertionError as err:
        # client broke business rules somehow
        return Response(err.message, status=status.HTTP_400_BAD_REQUEST)

    except (models.Article.DoesNotExist, models.ArticleVersion.DoesNotExist):
        # article with given ID doesn't exist
        raise Http404()
