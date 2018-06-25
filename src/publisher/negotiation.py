"""Adds a list of supported media types to Django REST so it
doesn't spaz out when you ask for a custom media article in the
Accept header.

Creates a series of objects in the publisher.negotiation module with names such as:
* ArticleListVersion1
* ArticleListVersion2
* POAArticleVersion1

etc"""

from rest_framework.renderers import JSONRenderer
#from rest_framework.exceptions import NotAcceptable
from .utils import lmap, lzip
import itertools
from django.http.multipartparser import parse_header
import logging

LOG = logging.getLogger(__name__)

_dynamic_types = [
    # prefix of the global variable name to create, media type, known version list
    ('ArticleList', 'application/vnd.elife.article-list+json', [None, 1]),
    ('POAArticle', 'application/vnd.elife.article-poa+json', [None, 2]),
    ('VORArticle', 'application/vnd.elife.article-vor+json', [None, 2]),
    ('ArticleHistory', 'application/vnd.elife.article-history+json', [None, 1]),
    ('ArticleRelated', 'application/vnd.elife.article-related+json', [None, 1]),
]

def min_max_version_range(version_list):
    version_list = version_list[:]
    version_list.remove(None)
    return list(range(min(version_list), max(version_list) + 1))

# creates an index of mime: version-list
# ll: {'application/vnd.elife.article-poa+json': [1, 2], ...}
MIME_VERSION_RANGE = {mime: min_max_version_range(version_list) for _, mime, version_list in _dynamic_types}
#from rest_framework.response import Response
#from rest_framework import status

class Anything(JSONRenderer):
    media_type = '*'
    
class VersionedRenderer(JSONRenderer):
    version_range = None

    # riffing off of JSONRenderer.get_indent:
    # https://github.com/encode/django-rest-framework/blob/a540acdc9552bcaf704371c3e1dee216059a221e/rest_framework/renderers.py#L55
    def valid_version(self, accepted_media_type, renderer_context):
        if not accepted_media_type:
            return

        mime_type, params = parse_header(accepted_media_type.encode('ascii'))
        try:
            # 'version' is optional, if provided we attempt to match it
            if not 'version' in params:
                return True

            # a version has been provided, test if it's valid and supported
            given_version = int(params['version'])
            if given_version in self.version_range:
                return True

            #raise NotAcceptable("version %r for mime %r not in supported range %r" % (given_version, mime_type, self.version_range))
        except (ValueError, KeyError, TypeError):
            LOG.debug("unparseable value for 'version': %s" % params['version'])

        #return super(VersionedRenderer, self).render(data, accepted_media_type, renderer_context)


from rest_framework.negotiation import DefaultContentNegotiation
# https://github.com/encode/django-rest-framework/blob/a68b37d8bc432fae37ef5880aec500002b59f565/rest_framework/negotiation.py#L24
class Foo(DefaultContentNegotiation):
    def select_parser(self, request, parsers):
        ret = super(Foo, self).select_parser(request, parsers)
        print('select parser',ret)
        return ret

    def select_renderer(self, request, renderers, format_suffix):
        ret = super(Foo, self).select_renderer(request, renderers, format_suffix)

        # REST framework doesn't check the *value* of the parameters.
        # in our case, if an unsupported mime version has been requested,
        # the general case is returned.
        # if we get an instance of a general case, and a version has been supplied

        inst, accepted_mime_type = ret
        #if 'version' in accepted_mime_type:
        #    raise NotAcceptable("version probided in accept header but specific version renderer not found. unsupported version")

        return ret


    
#
#
#

def mktype(row):
    nom, mime, version_list = row
    def gen_klass_name(version):
        if version:
            return "%sVersion%s" % (nom, version), "%s; version=%s" % (mime, version)
        return nom, mime
    klass_list = lmap(gen_klass_name, version_list)

    supported_version_range = MIME_VERSION_RANGE[mime]
    
    global_scope = globals()

    def gen_klass(klass_row):
        nom, mime = klass_row
        global_scope[nom] = type(nom, (JSONRenderer,), {'media_type': mime, 'version_range': supported_version_range})
        # ll: ('publisher.negotiation.ArticleListVersion1', 'application/vnd.elife.article-list+json; version=1')
        # we use the return type in settings.py
        return 'publisher.negotiation.%s' % nom, mime

    return lmap(gen_klass, klass_list)

# creates two lists from the pair returned in mktype.gen_klass
# these are used in core.settings
KNOWN_CLASSES, KNOWN_MIMES = lzip(*itertools.chain(*lmap(mktype, _dynamic_types)))
