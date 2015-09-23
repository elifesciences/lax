import json
from django.shortcuts import get_object_or_404, Http404
from annoying.decorators import render_to
import models, logic
from django.views.decorators.http import require_POST
from django.http import HttpResponse
import ingestor

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import serializers as szr

import logging
logger = logging.getLogger(__name__)

@render_to("publisher/landing.html")
def landing(request):
    return {}

@render_to("publisher/article-list.html")
def article_list(request):
    return {
        'article_list': models.Article.objects.all()
    }


#
# API
#

def rest_response(status, rest={}):
    msg = 'success'
    ec = str(status)[0]
    if ec == '4':
        msg = 'warning'
    elif ec == '5':
        msg = 'error'
    data = {'message': msg}
    data.update(rest)
    return Response(data, status=status)

def article_or_404(doi, version=None):
    try:
        return logic.article(doi, version)
    except models.Article.DoesNotExist:
        raise Http404("Article not found")


#
# collections of articles
#

@api_view(['GET'])
def corpus_info(rest_request):
    articles = models.Article.objects.all()
    return Response({'article-count': articles.count(),
                     'research-article-count': articles.filter(type='research-article').count()})

#
# specific articles
#

class ArticleSerializer(szr.ModelSerializer):
    class Meta:
        exclude = ('id', 'journal')
        model = models.Article

@api_view(['GET'])
def get_article(rest_request, doi, version=None):
    "Returns latest article data for the given doi or for a specific version."
    article = article_or_404(doi, version)
    return Response(ArticleSerializer(article).data)

@api_view(['GET'])
def get_article_versions(rest_request, doi):
    """
    Returns all versions of the requested article, grouped by version number.
    
    """
    article_list = logic.article_versions(doi)
    if not article_list:
        raise Http404()
    article_list = {obj.version: ArticleSerializer(obj).data for obj in article_list}
    return Response(article_list)


class ArticleAttributeValueSerializer(szr.Serializer):
    attribute = szr.CharField(max_length=50)
    attribute_value = szr.CharField(max_length=255)

@api_view(['POST'])
def add_update_article_attribute(rest_request, doi, extant_only=True):
    """Update article attributes with new values.
    ---
    request_serializer: ArticleAttributeValueSerializer
    """
    article = article_or_404(doi)
    keyval = rest_request.data
    key, val = keyval['attribute'], keyval['attribute_value']
    attribute = logic.add_update_article_attribute(article, key, val, extant_only)
    return Response(attribute)

@api_view(['GET'])
def get_article_attribute(rest_request, doi, attribute, extant_only=True):
    """Returns the requested article's attribute value as
    both `attribute:value` and `attribute: attribute, attribute_value: value`."""
    article = article_or_404(doi)
    val = logic.get_attribute(article, attribute)
    data = {
        'doi': article.doi,
        'attribute': attribute,
        'attribute_value': val,
        attribute: val}
    return Response(data)

#
# importing
#

class ArticleImportSerializer(szr.Serializer):
    name = szr.CharField(max_length=255)

@api_view(['POST'])
def import_article(rest_request):
    """
    Imports an article in eLife's EIF format: https://github.com/elifesciences/elife-eif-schema
    Returns the doi of the inserted/updated article
    ---
    request_serializer: ArticleImportSerializer
    """    
    try:
        article_obj = ingestor.import_article(logic.journal(), rest_request.data)
        return Response({'doi': article_obj.doi})
    except Exception:
        logger.exception("unhandled exception attempting to import EIF json")
        return rest_response(500)
