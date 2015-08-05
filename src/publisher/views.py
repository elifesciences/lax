import json
from django.shortcuts import get_object_or_404
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



class ArticleSerializer(szr.ModelSerializer):
    class Meta:
        model = models.Article

@api_view(['GET'])
def get_article(rest_request, doi):
    article = logic.article(doi=doi)
    if not article:
        raise Http404()
    return Response(ArticleSerializer(article).data)

@api_view(['POST'])
def import_article(rest_request):
    try:
        article_obj = ingestor.import_article(logic.journal(), rest_request.data)
        return Response({'doi': article_obj.doi})
    except Exception:
        logger.exception("unhandled exception!")
        return rest_response(500)




class ArticleAttributeSerializer(szr.Serializer):
    attribute = szr.CharField(max_length=50)
    attribute_value = szr.CharField(max_length=255)

@api_view(['POST'])
def add_article_attribute(rest_request, doi, extant_only=True):
    """
    asdf
    ---
    request_serializer: ArticleAttributeSerializer
    """
    article = get_object_or_404(models.Article, doi=doi)
    keyval = rest_request.data
    key, val = keyval['attribute'], keyval['attribute_value']
    logic.add_attribute_to_article(article, key, val, extant_only)
    data = {key: logic.get_attribute(article, key)}
    return Response(data)
        
@api_view(['GET'])
def get_article_attribute(rest_request, doi, attribute, extant_only=True):
    article = get_object_or_404(models.Article, doi=doi)
    val = logic.get_attribute(article, attribute)
    data = {
        'doi': article.doi,
        'attribute': attribute,
        'attribute_value': val,
        attribute: val}
    return Response(data)

