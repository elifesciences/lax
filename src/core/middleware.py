from django.conf import settings
import logging
from django.utils.deprecation import MiddlewareMixin

LOG = logging.getLogger(__name__)

CGROUPS = 'HTTP_X_CONSUMER_GROUPS'
EXPECTED_HEADERS = (CGROUPS, )

def set_authenticated(request, state):
    request.META[settings.KONG_AUTH_HEADER] = state

class KongAuthentication(MiddlewareMixin):
    def process_response(self, request, response):
        hdr = settings.KONG_AUTH_HEADER
        response[hdr] = request.META.get(hdr, False)
        return response

    def process_request(self, request):
        headers = {}

        # if request doesn't have all expected headers, strip auth
        header = CGROUPS
        if CGROUPS not in request.META:
            # no auth or invalid auth request, return immediately
            LOG.debug('header %r not found, refusing auth', CGROUPS)
            set_authenticated(request, state=False)
            return
        headers[CGROUPS] = str(request.META[CGROUPS])

        groups = [h.strip() for h in headers[CGROUPS].split(',')]

        LOG.debug('user groups: %s', groups)
        if 'admin' in groups or 'view-unpublished-content' in groups:
            LOG.debug('user groups: %s', groups)
            set_authenticated(request, state=True)
        else:
            LOG.debug('setting request as not authenticated')
            set_authenticated(request, state=False)

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
