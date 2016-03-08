from django.db.models import Q, F, Max
from django.conf.urls import include, url
from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse
import models, logic
from datetime import datetime, timedelta
from django.utils.feedgenerator import Rss201rev2Feed

import logging
LOG = logging.getLogger(__name__)

class RSSArticleFeedGenerator(Rss201rev2Feed):
    def rss_attributes(self):
        parent_attr_dict = super(RSSArticleFeedGenerator, self).rss_attributes()
        parent_attr_dict.update({
            'xmlns:dc': "http://purl.org/dc/elements/1.1/"})
        return parent_attr_dict

    def add_item_elements(self, handler, item):
        super(RSSArticleFeedGenerator, self).add_item_elements(handler, item)
        handler.addQuickElement("dc:date", item['pubdate'].isoformat())

class AbstractArticleFeed(Feed):
    feed_type = RSSArticleFeedGenerator
    title = "eLife Article Feeds"
    description = "eLife Article Feed"

    def link(self, obj):
        raise NotImplementedError()

    def get_object(self, request, *args, **kwargs):
        raise NotImplementedError()

    def items(self, obj):
        "returns a list of models.Article-list objects"
        raise NotImplementedError()

    def item_title(self, item):
        return item.title

    def item_pubdate(self, item):
        return item.datetime_published

    def copyright(self):
        return 'eLife Sciences Publications Ltd'

    #def licence(self):
    #    # http://www.rssboard.org/creative-commons
    #    return 'Creative Commons Attribution 4.0'


class SpecificArticleFeed(AbstractArticleFeed):

    def get_object(self, request, aid_list):
        aid_list = aid_list.split(',')
        print 'aids',aid_list
        doi_list = map(lambda aid: '10.7554/'+aid, aid_list)
        print 'doi',doi_list
        return {'aid_list': aid_list,
                'doi_list': doi_list}

    def link(self, obj):
        return reverse('rss-specific-article-list', kwargs={'aid_list': ','.join(obj['aid_list'])})

    def items(self, obj):
        return models.Article.objects.filter(doi__in=obj['doi_list']).order_by('-datetime_record_updated', 'version')

    def item_title(self, item):
        return u'%s (version %s)' % (item.title, item.version)


class RecentArticleFeed(AbstractArticleFeed):
    feed_type = RSSArticleFeedGenerator
    title = "eLife Article Feeds"
    description = "eLife Article Feed"

    def link(self, obj):
        return reverse('rss-recent-article-list', kwargs=obj['original'])

    def get_object(self, request, article_types, since):
        return {
            'original': {'article_types': article_types,
                         'since': since},
            'article_types': article_types.split('+'),
            'since': datetime.now() - timedelta(days=int(since))}

    def items(self, obj):
        where_clauses = [
            "datetime_published >= '%s'" % obj['since'].strftime('%Y-%m-%d %H-%M-%S'),
            "status in (%s)" % ', '.join(map(lambda v: "'%s'" % v, obj['article_types']))
        ]
        return logic.latest_articles(where=where_clauses)

#
# rss handling
#

# rooted at /rss/articles/ in urls.py
urls = [
    url(r"^(?P<aid_list>(eLife\.\d{5}[,]?)+)$", SpecificArticleFeed(), name='rss-specific-article-list'),
    url(r"^(?P<article_types>(poa\+vor)|(poa|vor))/last-(?P<since>\d{1,3})-days/$", RecentArticleFeed(), name='rss-recent-article-list'),

]

