from jsonschema import ValidationError
from django.db import transaction
from . import models, logic, fragment_logic
from .utils import ensure
from rest_framework import status
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
    resultset = map(logic.article_snippet_json, qs) # extract the article json
    struct = {
        'total': qs.count(), # pagination may f with us
        'items': resultset}
    return Response(struct, content_type='application/vnd.elife.articles-list+json;version=1')

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

#
# not part of public api
#

@api_view(['POST'])
def article_fragment(rest_request, art_id, fragment_id):
    only_published = False
    try:
        ensure(fragment_id != 'xml->json', "that key is taken")
        with transaction.atomic():
            av = logic.most_recent_article_version(art_id, only_published)
            data = rest_request.data
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
