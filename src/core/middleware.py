from django.conf import settings
from netaddr import IPAddress, IPNetwork
import logging

LOG = logging.getLogger(__name__)

EXPECTED_HEADERS = CGROUPS, CID, CUSER = 'x-consumer-groups', 'x-consumer-id', 'x-consumer-username'

def set_authenticated(request, state=False):
    request.META[settings.KONG_AUTH_HEADER] = state

def strip_auth_headers(request, authenticated=False):
    "strips the KONG auth headers for whatever reason. mutator"
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
        for header in EXPECTED_HEADERS:
            if header not in request.META:
                # no auth or invalid auth request, return immediately
                strip_auth_headers(request)
                return
            headers[header] = str(request.META[header])

        # if request not originating from within vpn, strip auth
        client_ip = IPAddress(request.META['REMOTE_ADDR'])
        internal_network = IPNetwork(settings.INTERNAL_NETWORK)
        if not client_ip in internal_network:
            strip_auth_headers(request)
            LOG.warn("your IP doesn't originate within internal network, refusing auth")
            return

        # if request doesn't have all expected headers, strip auth
        if len(headers.keys()) != len(EXPECTED_HEADERS):
            strip_auth_headers(request)
            LOG.warn("incorrect number of headers (%s) expecting (%s), refusing auth", len(headers.keys()), len(EXPECTED_HEADERS))
            return

        # if request has expected headers, but their values are invalid, strip auth
        if headers[CGROUPS] not in ['user', 'admin']:
            strip_auth_headers(request)
            LOG.warn("unknown user group, refusing auth")
            return

        # test the id somehow?

        # if their username is 'anonymous'
        if headers[CUSER] == 'anonymous':
            strip_auth_headers(request)
            LOG.warn("anonymous user, refusing auth")
            return

        strip_auth_headers(request, authenticated=True)
        LOG.info("authenticated!")
