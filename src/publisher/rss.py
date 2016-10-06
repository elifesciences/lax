from django.conf.urls import url
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
        pubdate = item['pubdate']
        if pubdate:
            handler.addQuickElement("dc:date", pubdate.isoformat())
        else:
            LOG.warn("no pubdate, skipping added a 'dc:date' element to rss feed", extra=item)

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
        return item.article.datetime_published

    def item_updateddate(self, item):
        return item.datetime_published

    def copyright(self):
        return 'eLife Sciences Publications Ltd'

    # def licence(self):
    #    # http://www.rssboard.org/creative-commons
    #    return 'Creative Commons Attribution 4.0'


class SpecificArticleFeed(AbstractArticleFeed):

    def get_object(self, request, aid_list):
        aid_list = aid_list.split(',')
        doi_list = map(lambda aid: '10.7554/' + aid, aid_list)
        return {'aid_list': aid_list,
                'doi_list': doi_list}

    def link(self, obj):
        return reverse('rss-specific-article-list', kwargs={'aid_list': ','.join(obj['aid_list'])})

    def items(self, obj):
        return models.ArticleVersion.objects \
            .select_related('article') \
            .filter(article__doi__in=obj['doi_list']) \
            .order_by('-datetime_published', 'version')

    def item_title(self, item):
        return u'%s (version %s)' % (item.title, item.version)


class RecentArticleFeed(AbstractArticleFeed):
    feed_type = RSSArticleFeedGenerator
    title = "eLife Article Feeds"
    description = "eLife Article Feed"

    def link(self, obj):
        return reverse('rss-recent-article-list', kwargs=obj['original'])

    def get_object(self, request, article_status, since):
        return {
            # used to conveniently generate the reverse url
            'original': {'article_status': article_status,
                         'since': since},
            'article_status': tuple(article_status.split('+')),
            'since': datetime.now() - timedelta(days=int(since))
        }

    def items(self, obj):
        kwargs = {
            'datetime_published__gte': obj['since'],  # .strftime('%Y-%m-%d'),
            'status__in': obj['article_status']
        }
        return logic.latest_article_versions().filter(**kwargs)

class AbstractReportFeed(AbstractArticleFeed):
    #feed_type = RSSArticleFeedGenerator

    def title(self, obj):
        return obj['title']

    def description(self, obj):
        return obj['description']

    def link(self, obj):
        return obj['url']

    def get_object(self, request):
        raise NotImplementedError("asdf")

    def items(self, obj):
        return obj['results']

    def item_title(self, item):
        return item['title']

    def item_link(self, item):
        return item['link']

    def item_description(self, item):
        return item['description']

    def item_author_name(self, item):
        return item['author']['name']

    def item_author_email(self, item):
        return item['author']['email']

    def item_pubdate(self, item):
        return item['pub-date']

    def item_updateddate(self, item):
        return item.get('update-date')

    def item_guid(self, item):
        return item['guid']

    def item_categories(self, item):
        return item['category-list']


#
# rss handling views
#

# rooted at /rss/articles/ in urls.py
urlpatterns = [
    url(r"^(?P<aid_list>(eLife\.\d{5}[,]?)+)$", SpecificArticleFeed(), name='rss-specific-article-list'),
    url(r"^(?P<article_status>(poa\+vor)|(poa|vor))/last-(?P<since>\d{1,3})-days/$", RecentArticleFeed(), name='rss-recent-article-list'),
]
