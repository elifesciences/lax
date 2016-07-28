from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def article_list(request):
    return Response([], content_type='application/vnd.elife.articles-list+json;version=1')

@api_view(['GET'])
def article(request, id):
    if True:
        return Response([], content_type='application/vnd.elife.article-poa+json;version=1')
    return Response([], content_type='application/vnd.elife.article-vor+json;version=1')

@api_view(['GET'])
def article_version_list(request, id):
    return Response([], content_type='application/vnd.elife.article-history+json;version=1')

@api_view(['GET'])
def article_version(request, id, version):
    if True:
        return Response([], content_type='application/vnd.elife.article-poa+json;version=1')
    else:
        return Response([], content_type='application/vnd.elife.article-vor+json;version=1')
