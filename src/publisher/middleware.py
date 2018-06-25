import json
from collections import OrderedDict
from django.conf import settings
import logging
from .utils import lmap

LOG = logging.getLogger(__name__)

# temporarily borrowed from bot-lax-adaptor...
def visit(data, pred, fn, coll=None):
    "visits every value in the given data and applies `fn` when `pred` is true "
    if pred(data):
        if coll is not None:
            data = fn(data, coll)
        else:
            data = fn(data)
        # why don't we return here after matching?
        # the match may contain matches within child elements (lists, dicts)
        # we want to visit them, too
    if isinstance(data, OrderedDict):
        results = OrderedDict()
        for key, val in data.items():
            results[key] = visit(val, pred, fn, coll)
        return results
    elif isinstance(data, dict):
        return {key: visit(val, pred, fn, coll) for key, val in data.items()}
    elif isinstance(data, list):
        return [visit(row, pred, fn, coll) for row in data]
    # unsupported type/no further matches
    return data

def visit_target(content, transformer):
    def pred(element):
        "returns True if given element is a target for transformation"
        if isinstance(element, dict):
            return 'additionalFiles' in element or 'sourceData' in element

    def fn(element):
        "transforms element's contents into something valid"
        for target in ['additionalFiles', 'assets', 'sourceData']:
            if target in element:
                element[target] = lmap(transformer, element[target])
        return element

    return visit(content, pred, fn)

def downgrade(content):
    "returns v1-compliant content"
    def transformer(item):
        if not 'title' in item:
            if 'label' in item:
                item['title'] = item['label']
                del item['label'] # good idea?
            else:
                # what title do we assign if we have no label?
                pass
        return item
    return visit_target(content, transformer)

'''
def upgrade(content):
    "returns v2-compliant content"
    def transformer(item):
        if not 'label' in item:
            item['label'] = item['title']
            del item['title']
        return item
    return visit_target(content, transformer)
'''

TRANSFORMS = {
    '1': downgrade,
    #'2': upgrade,
    #'*': upgrade, # accept ll: */*
}

# adapted from https://djangosnippets.org/snippets/1042/
def parse_accept_header(accept):
    """returns a list of triples, (media, key, val)
    for example: "application/vnd.elife.article-vor+json; version=2"
    returns: [("application/vnd.elife.article-vor+json", "version", "2")]

    and this: "application/vnd.elife.article-vor+json; version=1, application/vnd.elife.article-vor+json; version=2"
    returns: [("application/vnd.elife.article-vor+json", "version", "2"),
              ("application/vnd.elife.article-vor+json", "version", "1")]
    """
    result = []
    for media_range in accept.split(","):
        parts = media_range.split(";")
        media_type = parts.pop(0).strip().lower()
        for part in parts:
            key, val = part.lstrip().split("=", 1)
            result.append((media_type, key, val))
        # normalize requests with no version specified
        if not parts:
            result.append((media_type, 'version', '*')) # any version
    result.sort(key=lambda row: row[-1], reverse=True) # sorts rows by parameter values, highest first
    return result

def transformable(response):
    "exclude everything but api requests"
    if settings.API_V12_TRANSFORMS and getattr(response, 'content_type', False):
        # not present in redirects and such
        # target any response of content type:
        target = [
            'application/vnd.elife.article-poa+json',
            'application/vnd.elife.article-vor+json'
        ]
        for row in parse_accept_header(response.content_type):
            if row[0] in target:
                return True

def requested_version(request):
    "figures out which content version was requested. "
    targets = [
        'application/vnd.elife.article-poa+json',
        'application/vnd.elife.article-vor+json',
    ]
    bits = parse_accept_header(request.META.get('HTTP_ACCEPT', '*/*'))
    versions = []
    for row in bits:
        if row[0] in targets:
            # TODO: fragile, don't leave as-is
            versions.append(int(row[-1][0])) # last element, last character
    return '*' if not versions else max(versions)

def deprecated(request):
    if not settings.API_V12_TRANSFORMS:
        return False
    targets = [
        ('application/vnd.elife.article-poa+json', 'version', '1'),
        ('application/vnd.elife.article-vor+json', 'version', '1'),
    ]
    accepts = parse_accept_header(request.META.get('HTTP_ACCEPT', '*/*'))
    for target in targets:
        if target in accepts:
            return True

#
# middleware
#

def apiv12transform(get_response_fn):
    def middleware(request):
        response = get_response_fn(request)
        if transformable(response):
            version = requested_version(request)
            if version in TRANSFORMS:
                content = json.loads(response.content.decode('utf-8'))
                response.content = bytes(json.dumps(TRANSFORMS[version](content), ensure_ascii=False), 'utf-8')
        return response
    return middleware

def apiv1_deprecated(get_response_fn):
    def middleware(request):
        response = get_response_fn(request)
        if deprecated(request):
            response['warning'] = "Deprecation: Support for version 1 will be removed"
        return response
    return middleware


#
#
#
from django.http.multipartparser import parse_header

def flatten_accept(header):
    lst = []
    for mime in header.split(','):
        parsed_mime, parsed_params = parse_header(mime.encode())
        # ll: ('*/*', 'version', None)
        # ll: ('application/json', 'version', None)
        # ll: ('application/vnd.elife.article-poa+json', 'version', 2)
        lst.append((parsed_mime, 'version', parsed_params.pop('version', None)))

        
    return lst
        
#from rest_framework.response import Response
#from rest_framework.exceptions import NotAcceptable
from django.http import HttpResponse

def content_check(get_response_fn):
    def middleware(request):
        request_accept_header = request.META.get('HTTP_ACCEPT', '*/*')

        # REST Framework will block unacceptable types up to a point.
        # it will not discriminate on the *value* of a parameter (like 'version')

        client_accepts_list = flatten_accept(request_accept_header)

        # TODO: if unsupported version requested, raise 406 immediately
        # traversing a short list must be faster than querying a database
        # if we don't check here, it will be checked in the response

        response = get_response_fn(request)
        if response.status_code != 200:
            # unsuccessful response, ignore
            return response

        # successful response
        response_accept_header = response.content_type

        response_mime = flatten_accept(response_accept_header)[0]
        response_mime_general_case = response_mime[:2] + (None,)

        anything = ('*/*', 'version', None)
        almost_anything = ('application/*', 'version', None)

        acceptable = response_mime in client_accepts_list \
            or response_mime_general_case in client_accepts_list \
            or anything in client_accepts_list \
            or almost_anything in client_accepts_list

        #print(response_mime)
        #print(response_mime_general_case)
        #print(client_accepts_list)
        #print('acceptable?',acceptable)
        #print()

        if not acceptable:
            return HttpResponse("", content_type="application/problem+json", status=406)
            #res = Response("", status=406, content_type="application/problem+json")
            #res.render()
            #return res
            #raise NotAcceptable("asdf")
            response.status = 406
            return response

        return response
    return middleware
