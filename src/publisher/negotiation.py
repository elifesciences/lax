"""Adds a list of supported media types to Django REST so it
doesn't spaz out when you ask for a custom media article in the
Accept header.

Creates a series of objects in the publisher.negotiation module with names such as:
* ArticleListVersion1
* ArticleListVersion2
* POAArticleVersion1

etc"""

from rest_framework.renderers import JSONRenderer
from .utils import lmap

def mktype(row):
    nom, mime, version_list = row
    klass_list = lmap(lambda ver: ("%sVersion%s" % (nom, ver), "%s; version=%s" % (mime, ver)), version_list)
    global_scope = globals()

    def gen_klass(klass_row):
        nom, mime = klass_row
        global_scope[nom] = type(nom, (JSONRenderer,), {'media_type': mime})
    lmap(gen_klass, klass_list)

_dynamic_types = [
    # prefix of the global variable name to create, media type, known version list
    ('ArticleList', 'application/vnd.elife.article-list+json', [1, 2]),
    ('POAArticle', 'application/vnd.elife.article-poa+json', [1, 2]),
    ('VORArticle', 'application/vnd.elife.article-vor+json', [1, 2]),
    ('ArticleHistory', 'application/vnd.elife.article-history+json', [1, 2]),
    ('ArticleRelated', 'application/vnd.elife.article-related+json', [1, 2]),
]

lmap(mktype, _dynamic_types)
