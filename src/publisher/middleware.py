import json
from collections import OrderedDict
from django.conf import settings
import logging
from .utils import lmap
from rest_framework.response import Response as RESTResponse
from django.http import HttpResponse
from django.http.multipartparser import parse_header
LOG = logging.getLogger(__name__)

#
# utils
#

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

def get_content_type(resp):
    if isinstance(resp, HttpResponse):
        # Django response object used outside of REST framework
        return resp.get('Content-Type')
    elif isinstance(resp, RESTResponse):
        return resp.content_type

def flatten_accept(header, just_elife=False):
    lst = []
    for mime in header.split(','):
        parsed_mime, parsed_params = parse_header(mime.encode())
        # ll: ('*/*', 'version', None)
        # ll: ('application/json', 'version', None)
        # ll: ('application/vnd.elife.article-poa+json', 'version', 2)
        if just_elife and 'elife' not in parsed_mime:
            continue
        lst.append((parsed_mime, 'version', parsed_params.pop('version', None)))
    return lst

#
#
#

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
    1: downgrade,

    # all content has now been upgraded to v2.
    #'2': upgrade,
    #'*': upgrade, # accept ll: */*
}

def transformable(response):
    "exclude everything but api requests"
    content_type = get_content_type(response)
    if settings.API_V12_TRANSFORMS and content_type:
        # not present in redirects and such
        # target any response of content type:
        target = [
            'application/vnd.elife.article-poa+json',
            'application/vnd.elife.article-vor+json'
        ]
        for row in flatten_accept(content_type, just_elife=True):
            if row[0] in target:
                return True

def requested_version(request, response):
    """given a list of client-accepted mimes and the actual mime returned in the response,
    returns the max supported version or '*' if no version specified"""
    response_mime = flatten_accept(get_content_type(response))[0]
    bits = flatten_accept(request.META.get('HTTP_ACCEPT', '*/*'))
    versions = []
    for acceptable_mime in bits:
        if acceptable_mime[0] == response_mime[0] and acceptable_mime[-1]:
            versions.append(int(acceptable_mime[-1]))
    return (response_mime[0], '*' if not versions else max(versions))

def deprecated(request):
    if not settings.API_V12_TRANSFORMS:
        return False
    targets = [
        ('application/vnd.elife.article-poa+json', 'version', b'1'),
        ('application/vnd.elife.article-vor+json', 'version', b'1'),
    ]
    accepts = flatten_accept(request.META.get('HTTP_ACCEPT', '*/*'))
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
            mime, version = requested_version(request, response)
            if version in TRANSFORMS:
                content = json.loads(response.content.decode('utf-8'))
                content = bytes(json.dumps(TRANSFORMS[version](content), ensure_ascii=False), 'utf-8')
                new_content_type = "%s; version=%s" % (mime, version)

                new_response = HttpResponse(content, content_type=new_content_type)
                # this is where RESTResponses keep it
                # keeps some wrangling out of tests
                new_response.content_type = new_content_type

                # nothing here works: https://github.com/encode/django-rest-framework/blob/master/rest_framework/response.py
                #print('new content type', new_content_type)
                #response.content_type = new_content_type
                #response.__dict__['content_type'] = new_content_type
                #response.__dict__['Content-Type'] = new_content_type
                #setattr(response, 'Content-Type', new_content_type)
                # response.render()
                # print('>>',response) # should equal new content type, doesn't

                # not great, but I can't affect the content_type of the existing RESTResponse for some reason
                response = new_response
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

def content_check(get_response_fn):
    def middleware(request):
        request_accept_header = request.META.get('HTTP_ACCEPT', '*/*')

        # REST Framework will block unacceptable types up to a point.
        # it will not discriminate on the *value* of a parameter (like 'version')
        # this means, we can't automatically refuse version=1 of a particular mime
        # without rewriting or undermining a big chunk of their logic

        client_accepts_list = flatten_accept(request_accept_header)

        # TODO: if unsupported version requested, raise 406 immediately
        # traversing a short list must be faster than querying a database
        # if we don't check here, it will be checked in the response

        response = get_response_fn(request)
        if response.status_code != 200:
            # unsuccessful response, ignore
            return response

        # successful response
        anything = '*/*'
        response_accept_header = get_content_type(response) or anything

        # response accept header will always be a list with a single row
        response_mime = flatten_accept(response_accept_header)[0]
        response_mime_general_case = response_mime[:2] + (None,)

        anything = ('*/*', 'version', None)
        almost_anything = ('application/*', 'version', None)

        acceptable = response_mime in client_accepts_list \
            or response_mime_general_case in client_accepts_list \
            or anything in client_accepts_list \
            or almost_anything in client_accepts_list

        # print(response_mime)
        # print(response_mime_general_case)
        # print(client_accepts_list)
        # print('acceptable?',acceptable)
        # print()

        if not acceptable:
            # TODO
            return HttpResponse("", content_type="application/problem+json", status=406)
        return response
    return middleware
