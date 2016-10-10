from . import models, logic
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import Http404
from .models import POA

import logging
LOG = logging.getLogger(__name__)

def ctype(status):
    poa_ctype = 'application/vnd.elife.article-poa+json;version=1'
    vor_ctype = 'application/vnd.elife.article-vor+json;version=1'
    return poa_ctype if status == POA else vor_ctype

#
#
#

@api_view(['GET'])
def article_list(request):
    "returns a list of snippets"
    authenticated = False
    qs = logic.latest_article_versions(only_published=not authenticated)
    # TODO: paginate
    rs = map(logic.article_snippet_json, qs) # extract the article json
    return Response(rs, content_type='application/vnd.elife.articles-list+json;version=1')

@api_view(['GET'])
def article(request, id):
    "return the article-json for the most recent version of the given article ID"
    authenticated = False
    try:
        av = logic.most_recent_article_version(id, only_published=not authenticated)
        return Response(logic.article_json(av), content_type=ctype(av.status))
    except models.Article.DoesNotExist:
        raise Http404()

@api_view(['GET'])
def article_version_list(request, id):
    "returns a list of versions for the given article ID"
    authenticated = False
    try:
        resp = logic.article_version_history(id, only_published=not authenticated)
        return Response(resp, content_type='application/vnd.elife.article-history+json;version=1')
    except models.Article.DoesNotExist:
        raise Http404()

@api_view(['GET'])
def article_version(request, id, version):
    "returns the article-json for a specific version of the given article ID"
    try:
        av = logic.article_version(id, version)
        return Response(logic.article_json(av), content_type=ctype(av.status))
    except models.ArticleVersion.DoesNotExist:
        raise Http404()
