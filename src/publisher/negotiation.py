"""Adds a list of supported media types to Django REST so it
doesn't spaz out when you ask for a custom media article in the
Accept header.

Creates a series of objects in the publisher.negotiation module with names such as:
* ArticleListVersion1
* ArticleListVersion2
* POAArticleVersion1

etc"""

from rest_framework.renderers import JSONRenderer
from .utils import lmap, lzip
import itertools

def mktype(row):
    nom, mime, version_list = row
    klass_list = lmap(lambda ver: ("%sVersion%s" % (nom, ver), "%s; version=%s" % (mime, ver)), version_list)
    global_scope = globals()

    def gen_klass(klass_row):
        nom, mime = klass_row
        global_scope[nom] = type(nom, (JSONRenderer,), {'media_type': mime})
        # ll: ('publisher.negotiation.ArticleListVersion1', 'application/vnd.elife.article-list+json; version=1')
        # we use the return type in settings.py
        return 'publisher.negotiation.%s' % nom, mime
    return lmap(gen_klass, klass_list)


_dynamic_types = [
    # prefix of the global variable name to create, media type, known version list
    ('ArticleList', 'application/vnd.elife.article-list+json', [1]),
    ('POAArticle', 'application/vnd.elife.article-poa+json', [1, 2]),
    ('VORArticle', 'application/vnd.elife.article-vor+json', [1, 2]),
    ('ArticleHistory', 'application/vnd.elife.article-history+json', [1]),
    ('ArticleRelated', 'application/vnd.elife.article-related+json', [1]),
]

# create two lists from the pair returned in mktype.gen_klass
# these are used in core.settings
KNOWN_CLASSES, KNOWN_MIMES = lzip(*itertools.chain(*lmap(mktype, _dynamic_types)))
