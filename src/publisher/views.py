from os.path import join
import os
from django.conf import settings
import json
from django.shortcuts import get_object_or_404, Http404
from annoying.decorators import render_to
import models, logic
from django.views.decorators.http import require_POST
from django.http import HttpResponse
import ingestor, rss
from django.core.urlresolvers import reverse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import ParseError
from rest_framework import serializers as szr
from django.db.models import Q
from datetime import datetime, timedelta

import logging
LOG = logging.getLogger(__name__)

@render_to("publisher/landing.html")
def landing(request):
    project_root = os.path.abspath(join(settings.SRC_DIR, '..'))
    return {
        'readme': open(join(project_root, 'README.md')).read()
    }

#
# API
#

def article_or_404(doi, version=None):
    try:
        return logic.article(doi, version)
    except models.Article.DoesNotExist:
        raise Http404("Article not found")


#
# API, collections of articles
#

@api_view(['GET'])
def corpus_info(rest_request):
    articles = models.Article.objects.all()
    return Response({'article-count': articles.count(),
                     'research-article-count': articles.filter(type='research-article').count()})

#
# API, specific articles
#

class ArticleSerializer(szr.ModelSerializer):
    
    class Meta:
        exclude = ('id', 'journal')
        model = models.Article

class ArticleVersionSerializer(szr.ModelSerializer):
    article = ArticleSerializer()

    def to_representation(self, obj):
        res = super(ArticleVersionSerializer, self).to_representation(obj)
        res.update(res['article'])
        del res['article']
        return res
    
    class Meta:
        model = models.ArticleVersion
        exclude = ('id',)



@api_view(['GET'])
def get_article(rest_request, doi, version=None):
    "Returns latest article data for the given doi or for a specific version."
    article, version = article_or_404(doi, version)
    return Response(ArticleVersionSerializer(version).data)

@api_view(['GET'])
def get_article_versions(rest_request, doi):
    """
    Returns all versions of the requested article, grouped by version number.
    
    """
    article_list = logic.article_versions(doi)
    if not article_list:
        raise Http404()
    article_list = {obj.version: ArticleVersionSerializer(obj).data for obj in article_list}
    return Response(article_list)


class ArticleAttributeValueSerializer(szr.Serializer):
    attribute = szr.CharField(max_length=50)
    attribute_value = szr.CharField(max_length=255)
    version = szr.IntegerField(required=False)

@api_view(['POST'])
def add_update_article_attribute(rest_request, doi, extant_only=True):
    """Update article attributes with new values.
    ---
    request_serializer: ArticleAttributeValueSerializer
    """
    keyval = rest_request.data
    key, val, version = keyval['attribute'], keyval['attribute_value'], keyval.get('version')
    article, version = article_or_404(doi, version)
    attribute = logic.add_update_article_attribute(article, key, val, extant_only)
    return Response(attribute)

@api_view(['GET'])
def get_article_attribute(rest_request, doi, attribute, extant_only=True):
    """Returns the requested article's attribute value as
    both `attribute:value` and `attribute: attribute, attribute_value: value`."""
    article, version = article_or_404(doi)
    val = logic.get_attribute(article, attribute)
    data = {
        'doi': article.doi,
        'attribute': attribute,
        'attribute_value': val,
        attribute: val}
    return Response(data)

#
# API, importing
#

@api_view(['POST'])
def import_article(rest_request, create=True, update=True):
    """
    Imports (creates or updates) an article in eLife's EIF format:
    https://github.com/elifesciences/elife-eif-schema
    
    Returns the doi of the inserted/updated article
    """
    try:
        article, version = ingestor.import_article(logic.journal(), rest_request.data, create, update)
        return Response({'doi': article.doi})
    except (ParseError, ValueError), e:
        return Response({"message": "failed to parse given JSON"}, status=400)
    except AssertionError:
        return Response({"message": "failed to create/update article"}, status=400)
    except models.Article.DoesNotExist:
        return Response({"message": "failed to find article to update it"}, status=404)
    
    except Exception:
        LOG.exception("unhandled exception attempting to import EIF json")
        return Response(None, status=500)

@api_view(['POST'])
def create_article(rest_request):
    return import_article(rest_request, create=True, update=False)

@api_view(['POST'])
def update_article(rest_request):
    return import_article(rest_request, create=False, update=True)

#
# reports
#

from . import reports
import csv
from django.http import StreamingHttpResponse
# https://docs.djangoproject.com/en/1.9/howto/outputting-csv/

class Echo(object):
    "An object that implements just the write method of the file-like interface."
    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value

def streaming_csv_response(filename, rows):
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse((writer.writerow(row) for row in rows), \
                                     content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename
    return response

# /reports/published.csv
def article_poa_vor_pubdates(request):
    return streaming_csv_response("published", reports.article_poa_vor_pubdates())

def time_to_publication(request):
    return streaming_csv_response("time-to-publication", reports.time_to_publication())


class PAWRecentReport(rss.AbstractReportFeed):
    def get_object(self, request, days_ago=None):
        if not days_ago:
            days_ago = 28
        limit = Q(datetime_published__gte=datetime.now() - timedelta(days=int(days_ago)))
        return {
            'title': 'PAW article data',
            'url': reverse('paw-recent-report', kwargs={'days_ago': days_ago}),
            'description': 'asdf',
            'params': None,
            'results': reports.paw_recent_data(limit)
        }

class PAWAheadReport(rss.AbstractReportFeed):
    def get_object(self, request, days_ago=None):
        if not days_ago:
            days_ago = 28
        limit = Q(datetime_published__gte=datetime.now() - timedelta(days=int(days_ago)))
        return {
            'title': 'PAW article data',
            'url': reverse('paw-ahead-report', kwargs={'days_ago': days_ago}),
            'description': 'asdf',
            'params': None,
            'results': reports.paw_ahead_data(limit)
        }
