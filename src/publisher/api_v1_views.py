from django.shortcuts import Http404
import models, logic
import eif_ingestor
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.parsers import ParseError
from rest_framework import serializers as szr

import logging
LOG = logging.getLogger(__name__)

def article_or_404(doi, version=None):
    try:
        return logic.article(doi, version)
    except models.Article.DoesNotExist:
        raise Http404("Article not found")


#
# API, collections of articles
#

'''
@api_view(['GET'])
def corpus_info(rest_request):
    articles = models.Article.objects.all()
    return Response({'article-count': articles.count(),
                     'research-article-count': articles.filter(type='research-article').count()})
'''

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
        exclude = ('id', 'article_json_v1', 'article_json_v1_snippet')

@api_view(['GET'])
def get_article(rest_request, doi, version=None):
    "Returns latest article data for the given doi or for a specific version."
    article, version = article_or_404(doi, version)
    return Response(ArticleVersionSerializer(version).data)

@api_view(['GET'])
def get_article_versions(rest_request, doi):
    "Returns all versions of the requested article, grouped by version number."
    article_list = logic.article_versions(doi)
    if not article_list:
        raise Http404()
    article_list = {obj.version: ArticleVersionSerializer(obj).data for obj in article_list}
    return Response(article_list)

#
# importing
#

@api_view(['POST'])
def import_article(rest_request, create=True, update=True):
    """
    Imports (creates or updates) an article in eLife's EIF format:
    https://github.com/elifesciences/elife-eif-schema

    Returns the doi of the inserted/updated article
    """
    try:
        article, version = eif_ingestor.import_article(logic.journal(), rest_request.data, create, update)
        return Response({'doi': article.doi})
    except (ParseError, ValueError):
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
