from django.conf import settings
from netaddr import IPAddress, IPNetwork
import logging

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

class KongAuthentication(object):
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

        # if request not originating from within vpn, strip auth
        client_ip = IPAddress(request.META['REMOTE_ADDR'])
        internal_networks = [IPNetwork(n) for n in settings.INTERNAL_NETWORKS]
        in_internal_networks = len([n for n in internal_networks if client_ip in n]) > 0
        if not internal_networks:
            strip_auth_headers(request)
            LOG.debug("IP doesn't originate within internal network, refusing auth: %s" % request.META['REMOTE_ADDR'])
            return

        # if request has expected headers, but their values are invalid, strip auth
        if headers[CGROUPS] not in ['user', 'admin']:
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
