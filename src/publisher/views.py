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
    article = get_object_or_404(models.Article, doi=doi)
    return Response(ArticleSerializer(article).data)

@api_view(['POST'])
def import_article(rest_request):
    try:
        ingestor.import_article(logic.journal(), rest_request.data)
        return rest_response(200)
    except Exception:
        logger.exception("unhandled exception!")
        return rest_response(500)

@api_view(['GET', 'POST'])
def article_attribute(rest_request, doi, extant_only=True):
    article = get_object_or_404(models.Article, doi=doi)
    keyval = rest_request.data
    # fetch the attribute
    if rest_request.method == 'GET':
        data = {keyval['key']: logic.get_attribute(article, keyval['key'])}
        return rest_response(200, data)

    # update the attribute
    logic.add_attribute_to_article(article, keyval['key'], keyval['val'], extant_only)
    data = {keyval['key']: logic.get_attribute(article, keyval['key'])}
    return rest_response(200, data)
        
    
