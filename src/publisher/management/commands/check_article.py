"""
temporary command to check one or more articles inside lax match the website.
this command will be removed or replaced when we switch to the new infrastructure.

usage: ./manage.sh check_article --msid 12345 01234 00123 00012 00001

"""

from functools import wraps
from django.core.management.base import BaseCommand
from publisher.utils import ensure, json_dumps
from publisher import models
import os
from os.path import join
#from datetime import datetime
import requests
from scrapy.selector import Selector
import re
import logging

logging.getLogger("requests").setLevel(logging.WARNING)
LOG = logging.getLogger(__name__)

OUTPUT_DIR = '.scrapy-cache'

def fname(msid):
    msid = str(int(msid)) # normalize value, strip any leading zeroes
    return join(OUTPUT_DIR, '%s-article-info.html' % msid)

def slurp(msid):
    "download the article page for a given elife doi, write content to disk"
    if os.path.exists(fname(msid)):
        return

    doi = "10.7554/eLife.%s" % str(msid).zfill(5)
    # ll: https://elifesciences.org/lookup/doi/10.7554/eLife.17267
    url = "https://elifesciences.org/lookup/doi/" + doi
    LOG.debug(url)
    resp = requests.get(url, allow_redirects=False)
    ensure(resp.status_code != 404, "404 fetching article: %s" % resp.status_code)
    art_info_url = resp.headers['Location'] + "/article-info"
    resp2 = requests.get(art_info_url)

    with open(fname(msid), 'wb') as handle:
        handle.write(resp2.content)


def complement(pred):
    @wraps(pred)
    def wrapper(*args, **kwargs):
        return not pred(*args, **kwargs)
    return wrapper

def splitfilter(func, data):
    return filter(func, data), filter(complement(func), data)


class Command(BaseCommand):
    help = '''Repopulates the lax database using the contents of the elife-publishing-eif bucket. If article has multiple attempts, use the most recent attempt. Matching PUBLISHED articles will be downloaded and imported using the `import_articles` command. Published status is determined by an entry in the elife-publishing-archive bucket'''

    def add_arguments(self, parser):
        parser.add_argument('--msid', dest='msid-list', type=int, nargs='+', required=True)

    def report(self, msid):
        context = {
            'msid': msid,
            'in-database': False,
            'unpublished-versions': [],
            'published-versions': [],

            'on-website': False,
            'web-published-versions': [],

            'state': 'unknown'
        }

        try:
            art = models.Article.objects.get(manuscript_id=msid)
            context['in-database'] = True

            avlist = art.articleversion_set.all()
            pub, unpub = splitfilter(lambda av: av.datetime_published, avlist)
            context['published-versions'] = map(lambda av: av.version, pub)
            context['unpublished-versions'] = map(lambda av: av.version, unpub)

        except models.Article.DoesNotExist:
            pass

        try:
            if not os.path.exists(fname(msid)):
                slurp(msid)
            context['on-website'] = True
        except AssertionError:
            context['on-website'] = False

        if context['on-website']:
            # scrape the website results, look for version history
            with open(fname(msid), 'r') as handle:
                contents = handle.read()
                obj = Selector(text=contents)
                root = obj.css("#panels-ajax-tab-container-elife-research-article-tabs ul.issue-toc-list li")
                values = root.css("::text").extract()
                cregex = re.compile(r"Version (?P<version>\d?) \((?P<datestr>.*)\)")
                matches = map(lambda v: cregex.search(v).groupdict(), values)

                def fn(match):
                    #dateobj = datetime.strptime(match['datestr'], "%B %d, %Y")
                    return int(match['version'])
                    # return {
                    #    'version': match['version'],
                    #    'pub-date': dateobj.strftime("%Y-%m-%d"),
                    #}
                versions = map(fn, matches)
                if not versions:
                    # article exists BUT it has no version history yet, so assume a v1
                    versions = [1]
                context['web-published-versions'] = versions

        LOG.debug("finished %s report" % msid, extra=context)

        c = context

        if not c['on-website']:
            # not published, nothing to compare against yet
            return context

        if not c['in-database']:
            # article is on website but not in database
            context['state'] = 'article ingest missing in lax'
            return context

        # article is on website and in database
        # compare versions

        # TODO: case where ingest has happened in lax, but not PUBLISH and website has published article

        lax_pv, web_pv = c['published-versions'], c['web-published-versions']

        if len(lax_pv) > len(web_pv):
            # there are more versions in lax than in website!
            missing_versions = set(lax_pv) - set(web_pv)
            context['state'] = 'website is missing published versions (%s)' % ', '.join(map(str, missing_versions))
            return context

        if len(lax_pv) < len(web_pv):
            missing_versions = set(web_pv) - set(lax_pv)
            context['state'] = 'lax is missing published versions (%s)' % ', '.join(map(str, missing_versions))
            return context

        # both lax and web are reporting the same number of published versions
        # ensure version lists are identical
        if sorted(lax_pv) != sorted(web_pv):
            context['state'] = 'lax has versions (%s) and website has versions (%s)' % (lax_pv, web_pv)
            return context

        context['state'] = 'no problems detected'

        return context

    def handle(self, *args, **options):
        try:
            msid_list = options['msid-list']
            results = dict(zip(msid_list, map(self.report, options['msid-list'])))
            self.stdout.write(json_dumps(results, indent=4))
            self.stdout.flush()
            exit(0)
        except Exception as err:
            LOG.exception("unhandled exception generating article report: %s", err)
            exit(1)
