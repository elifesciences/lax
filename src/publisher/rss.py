from django.db.models import Q, F, Max
from django.conf.urls import include, url
from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse
import models, logic
from datetime import datetime, timedelta
from django.utils.feedgenerator import Rss201rev2Feed

import logging
LOG = logging.getLogger(__name__)

def type_fn(article_types):
    "returns a django Q object that filters on article.status"
    return ', '.join(map(lambda v: "'%s'" % v, article_types))

class RSSArticleFeedGenerator(Rss201rev2Feed):
    def rss_attributes(self):
        parent_attr_dict = super(RSSArticleFeedGenerator, self).rss_attributes()
        parent_attr_dict.update({
            'xmlns:dc': "http://purl.org/dc/elements/1.1/"})
        return parent_attr_dict

    def add_item_elements(self, handler, item):
        super(RSSArticleFeedGenerator, self).add_item_elements(handler, item)
        handler.addQuickElement("dc:date", item['pubdate'].isoformat())

class ArticleFeed(Feed):
    feed_type = RSSArticleFeedGenerator
    title = "eLife Article Feeds"
    description = "eLife Article Feed"

    def link(self, obj):
        return reverse('rss-articles', kwargs=obj['original'])

    def get_object(self, request, article_types, since):
        return {
            'original': {'article_types': article_types,
                         'since': since},
            'article_types': article_types.split('+'),
            'since': datetime.now() - timedelta(days=int(since))}

    def items(self, obj):
        where_clauses = [
            "datetime_published >= '%s'" % obj['since'].strftime('%Y-%m-%d %H-%M-%S'),
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

