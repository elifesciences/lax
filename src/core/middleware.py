from django.conf import settings
import logging
from django.utils.deprecation import MiddlewareMixin

LOG = logging.getLogger(__name__)

# TODO: possibly remove everything different from CGROUPS, these values should not be depended upon by Lax
CGROUPS, CID, CUSER = 'HTTP_X_CONSUMER_GROUPS', 'HTTP_X_CONSUMER_ID', 'HTTP_X_CONSUMER_USERNAME'
EXPECTED_HEADERS = (CGROUPS, )

def set_authenticated(request, state=False):
    request.META[settings.KONG_AUTH_HEADER] = state

def strip_auth_headers(request, authenticated=False):
    "strips the KONG auth headers, set authentication status"
    for header in EXPECTED_HEADERS:
        if header in request.META:
            del request.META[header]
    set_authenticated(request, authenticated)

class KongAuthentication(MiddlewareMixin):
    def process_response(self, request, response):
        hdr = settings.KONG_AUTH_HEADER
        response[hdr] = request.META.get(hdr, False)
        return response

    def process_request(self, request):
        headers = {}

        # if request doesn't have all expected headers, strip auth
        for header in EXPECTED_HEADERS:
            if header not in request.META:
                # no auth or invalid auth request, return immediately
                LOG.debug('header %r not found, refusing auth', header)
                strip_auth_headers(request)
                return
            headers[header] = str(request.META[header])

        groups = [h.strip() for h in headers[CGROUPS].split(',')]

        # if request has expected headers, but their values are invalid, strip auth
        if not 'admin' in groups and not 'view-unpublished-content' in groups:
            strip_auth_headers(request)
            LOG.debug("unknown user group, refusing auth")
            return

        # if user is 'just' a user
        if headers[CGROUPS] == 'user':
            strip_auth_headers(request)
            LOG.debug("'user' group receives has no special permissions")
            return

        strip_auth_headers(request, authenticated=True)
        LOG.debug("authenticated!")

#
#
#

from django.views.decorators.cache import patch_cache_control
from django.utils.cache import patch_vary_headers

class DownstreamCaching(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        public_headers = {
            'public': True,
            'max-age': 60 * 5, # 5 minutes, 300 seconds
            'stale-while-revalidate': 60 * 5, # 5 minutes, 300 seconds
            'stale-if-error': (60 * 60) * 24, # 1 day, 86400 seconds
        }
        private_headers = {
            'private': True,
            'max-age': 0, # seconds
            'must-revalidate': True,
        }

        authenticated = request.META[settings.KONG_AUTH_HEADER]
        headers = public_headers if not authenticated else private_headers

        response = self.get_response(request)

        if not response.get('Cache-Control'):
            patch_cache_control(response, **headers)
        patch_vary_headers(response, ['Accept'])

        return response
