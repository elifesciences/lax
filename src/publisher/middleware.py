from collections import OrderedDict
from django.conf import settings
import logging

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

#
#
#

def downgrade(content):
    "returns v1-compliant content"

    def pred(element):
        # Figures, Supplementary files
        return True

    def fn(element):
        return element

    return visit(content, pred, fn)

def upgrade(content):
    "returns v2-compliant content"
    return content

TRANSFORMS = {
    '1': downgrade,
    '2': upgrade,
    '*': upgrade, # accept ll: */*
}

def transformable(request):
    "exclude everything but api requests"
    if settings.API_V12_TRANSFORMS:
        # more checks ...
        reqpath = request.META['PATH_INFO']
        return reqpath.startswith('/api/v2/')

def apiv12transform(get_response_fn):

    def middleware(request):
        response = get_response_fn(request)
        if transformable(request):
            # 'application/vnd.elife.article-vor+json; version=1, ...' =>
            # ['application/vnd.elife.article-vor+json; version=1', '...'] =>
            # 'application/vnd.elife.article-vor+json; version=1' =>
            # '1'
            accepts = request.META.get('HTTP_ACCEPT', '*/*')
            version = accepts.split(',')[0][-1]
            #LOG.info('got %s', accepts)
            response.content = TRANSFORMS[version](response.content)
            return response
        return response

    return middleware

'''
{'environ': {'wsgi.input': <django.test.client.FakePayload object at 0x7f01da5910f0>, 'PATH_INFO': '/api/v2/articles/16695/versions/1', 'SCRIPT_NAME': '', 'wsgi.errors': <_io.BytesIO object at 0x7f01da931990>, 'HTTP_COOKIE': '', 'SERVER_PROTOCOL': 'HTTP/1.1', 'REMOTE_ADDR': '127.0.0.1', 'wsgi.run_once': False, 'wsgi.multiprocess': True, 'HTTP_ACCEPT': 'application/vnd.elife.article-vor+json; version=1', 'wsgi.multithread': False, 'QUERY_STRING': '', 'KONG-Authenticated': False, 'REQUEST_METHOD': 'GET', 'SERVER_PORT': '80', 'wsgi.url_scheme': 'http', 'SERVER_NAME': 'testserver', 'wsgi.version': (1, 0)}, 'session': <django.contrib.sessions.backends.db.SessionStore object at 0x7f01da5912b0>, '_messages': <django.contrib.messages.storage.fallback.FallbackStorage object at 0x7f01da591198>, 'method': 'GET', 'path_info': '/api/v2/articles/16695/versions/1', '_dont_enforce_csrf_checks': True, '_post_parse_error': False, 'content_type': '', '_stream': <django.core.handlers.wsgi.LimitedStream object at 0x7f01da591358>, 'path': '/api/v2/articles/16695/versions/1', 'user': <SimpleLazyObject: <function AuthenticationMiddleware.process_request.<locals>.<lambda> at 0x7f01da5e4c80>>, '_read_started': False, 'content_params': {}, 'COOKIES': {}, 'resolver_match': None, 'META': {'wsgi.input': <django.test.client.FakePayload object at 0x7f01da5910f0>, 'PATH_INFO': '/api/v2/articles/16695/versions/1', 'SCRIPT_NAME': '', 'wsgi.errors': <_io.BytesIO object at 0x7f01da931990>, 'HTTP_COOKIE': '', 'SERVER_PROTOCOL': 'HTTP/1.1', 'REMOTE_ADDR': '127.0.0.1', 'wsgi.run_once': False, 'wsgi.multiprocess': True, 'HTTP_ACCEPT': 'application/vnd.elife.article-vor+json; version=1', 'wsgi.multithread': False, 'QUERY_STRING': '', 'KONG-Authenticated': False, 'REQUEST_METHOD': 'GET', 'SERVER_PORT': '80', 'wsgi.url_scheme': 'http', 'SERVER_NAME': 'testserver', 'wsgi.version': (1, 0)}}
'''
