"""Adds a list of supported media types to Django REST so it
doesn't spaz out when you ask for a custom media article in the
Accept header.

Creates a series of objects in the publisher.negotiation module with names such as:
* ArticleListVersion1
* ArticleListVersion2
* POAArticleVersion1

etc"""

from rest_framework import parsers
from rest_framework.renderers import JSONRenderer
from .utils import lmap, lzip
import itertools
import logging

LOG = logging.getLogger(__name__)

_dynamic_types = [
    # prefix of the global variable name to create, media type, known version list
    ('ArticleList', 'application/vnd.elife.article-list+json', [None, 1]),
    ('POAArticle', 'application/vnd.elife.article-poa+json', [None, 1, 2]),
    ('VORArticle', 'application/vnd.elife.article-vor+json', [None, 1, 2]),
    ('ArticleHistory', 'application/vnd.elife.article-history+json', [None, 1]),
    ('ArticleRelated', 'application/vnd.elife.article-related+json', [None, 1]),
]

def mktype(row):
    nom, mime, version_list = row

    def gen_klass_name(version):
        if version:
            return "%sVersion%s" % (nom, version), "%s; version=%s" % (mime, version)
        return nom, mime
    klass_list = lmap(gen_klass_name, version_list)

    global_scope = globals()

    def gen_klass(klass_row):
        nom, mime = klass_row
        global_scope[nom] = type(nom, (JSONRenderer,), {'media_type': mime})
        # ll: ('publisher.negotiation.ArticleListVersion1', 'application/vnd.elife.article-list+json; version=1')
        # we use the return type in settings.py
        return 'publisher.negotiation.%s' % nom, mime

    return lmap(gen_klass, klass_list)

# creates two lists from the pair returned in mktype.gen_klass
# these are used in core.settings
KNOWN_CLASSES, KNOWN_MIMES = lzip(*itertools.chain(*lmap(mktype, _dynamic_types)))


# ---

class POAParser(parsers.JSONParser):
    media_type = 'application/vnd.elife.article-poa+json'

class VORParser(parsers.JSONParser):
    media_type = 'application/vnd.elife.article-vor+json'
