import json
from django.shortcuts import render
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
        raise
        return response(400)
    except Exception, e:
        logger.exception("unhandled exception!")
        # unhandled exception, raise 500
        return response(500)
