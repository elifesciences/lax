import json
from django.shortcuts import get_object_or_404
from annoying.decorators import render_to
import models, logic
from django.views.decorators.http import require_POST
from django.http import HttpResponse
import ingestor

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

def response(status):
    resp = HttpResponse()
    resp.status_code = status
    return resp


from rest_framework.decorators import api_view
from rest_framework.response import Response

def rest_response(status, **rest):
    msg = 'success'
    ec = str(status)[0]
    if ec == '4':
        msg = 'warning'
    elif ec == '5':
        msg = 'error'
    data = {'message': msg}
    data.update(rest)
    return Response(data, status=status)



@api_view(['POST'])
def import_article(rest_request):
    try:
        ingestor.import_article(logic.journal(), rest_request.data)
        return rest_response(200)
    except Exception:
        logger.exception("unhandled exception!")
        return rest_response(500)

@api_view(['POST'])
def add_attribute(rest_request, doi, extant_only=True):
    try:
        article = get_object_or_404(models.Article, doi=doi)
        keyval = rest_request.data
        logic.add_attribute_to_article(article, keyval['key'], keyval['val'], extant_only)
        return rest_response(200)
    except models.AttributeType.DoesNotExist:
        # tried to add a new attribute without turning extant_only off
        return rest_response(400)
    except Exception:
        logger.exception("unhandled exception attempting to add attribute to an article")
        return rest_response(500)
