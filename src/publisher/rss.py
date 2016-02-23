from django.db.models import Q, F, Max
from django.conf.urls import include, url
from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse
import models, logic
from datetime import datetime, timedelta

import logging
LOG = logging.getLogger(__name__)

def since_fn(since_int):
    "returns a datetime object for the given string relative to datetime.now()"
    dt = datetime.now() - timedelta(days=int(since_int))
    return dt.strftime('%Y-%m-%d %H-%M-%S')

def type_fn(type_str):
    "returns a django Q object that filters on article.status"
    return ', '.join(map(lambda v: "'%s'" % v, type_str.split('+')))

class ArticleFeed(Feed):
    title = "eLife Article Feeds"
    description = "eLife Article Feed"

    def link(self, obj):
        return reverse('rss-articles', kwargs=obj)

    def get_object(self, request, article_types, since):
        return {'article_types': article_types,
                'since': since}

    def items(self, obj):
        where_clauses = [
            "datetime_published >= '%s'" % since_fn(obj['since']),
            "status in (%s)" % type_fn(obj['article_types']),
        ]
        return logic.latest_articles(where=where_clauses)

    def item_title(self, item):
        return item.title + ' v' + str(item.version)

    def item_pubdate(self, item):
        return item.datetime_published

    def copyright(self):
        return 'eLife Sciences Publications Ltd'

    #def licence(self):
    #    # http://www.rssboard.org/creative-commons
    #    return 'Creative Commons Attribution 4.0'

#
# rss handling
#

urls = [
    url("^(?P<article_types>(poa\+vor)|(poa|vor))/last-(?P<since>\d{1,3})-days/$", ArticleFeed(), name='rss-articles'),
]

