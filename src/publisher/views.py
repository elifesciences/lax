import json
from django.shortcuts import get_object_or_404
from annoying.decorators import render_to
import models, logic
from django.views.decorators.http import require_POST
from django.http import HttpResponse
import json_import as ingestor

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

@require_POST
def import_article(request):
    try:
        article_data = json.loads(request.body)
        ingestor.import_article(logic.journal(), article_data)
        return response(200)
    except ValueError:
        # json couldn't be decoded, user fail, raise 400
        return response(400)
    except Exception:
        logger.exception("unhandled exception!")
        # unhandled exception, raise 500
        return response(500)

@require_POST
def add_attribute(request, doi, version, extant_only=True):
    if not version:
        version = 1
    try:
        article = get_object_or_404(models.Article, doi=doi, version=version)
        keyval = json.loads(request.body)
        logic.add_attribute_to_article(article, keyval['key'], keyval['val'], extant_only)
        return response(200)
    except models.AttributeType.DoesNotExist:
        # tried to add a new attribute without turning extant_only off
        return response(400)
    except Exception:
        logger.exception("unhandled exception attempting to add attribute to an article")
        return response(500)
