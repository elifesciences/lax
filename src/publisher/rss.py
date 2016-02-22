from django.db.models import Q
from django.conf.urls import include, url
from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse
import models, logic
from datetime import datetime

import logging
LOG = logging.getLogger(__name__)

# '/rss/articles/((poa|vor)|(poa+vor))/',
# '/rss/articles/((poa|vor)|(poa+vor))/(24-hours|last-seven-days|last-28-days|last-168-days|last-365-days)/',
# '/rss/articles/((poa|vor)|(poa+vor))/(today|this-week|last-week|this-month|last-month|last-six-months|this-year|last-year)/'

since_list = [
    "24-hours"
    "last-seven-days"
    "last-28-days",
    "last-168-days",
    "last-365-days",

    "today",
    "this-week",
    "last-week",
    "this-month",
    "last-month",
    "last-six-months",
    "this-year",
]

def since_fn(since_str):
    "returns a datetime object for the given string relative to datetime.now()"
    if since_str == 'today':
        return datetime.now().replace(hour=0, minute=0, second=0)
    elif since_str == '24-hours':
        return datetime.now() - timedelta(hours=24)
    return None

def type_q(type_str):
    "returns a django Q object that filters on article.status"
    return Q(status__in=type_str.split('+'))

class ArticleFeed(Feed):
    title = "eLife Article Feeds"
    description = "eLife Article Feed"

    def link(self, obj):
        return reverse('rss-articles', kwargs=obj)

    def get_object(self, request, article_types, since):
        return {'article_types': article_types,
                'since': since}

    def items(self, obj):
        limit_qobj = Q(datetime_published__gte=since_fn(obj['since']))
        type_qobj = type_q(obj['article_types'])
        return models.Article.objects.filter(type_qobj).filter(limit_qobj)

    def item_title(self, item):
        return item.title

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

since_list_str = "(%s)" % "|".join(since_list)

urls = [
    url("^(?P<article_types>(poa\+vor)|(poa|vor))/(?P<since>%s)/$" % since_list_str, ArticleFeed(), name='rss-articles'),
]

