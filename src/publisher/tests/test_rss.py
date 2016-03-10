import re
from base import BaseCase
from django.test import Client
from django.core.urlresolvers import reverse
from publisher import logic
from datetime import datetime, timedelta

class RSSViews(BaseCase):
    def setUp(self):
        self.c = Client()
        self.journal = logic.journal()
        an_hour_ago = datetime.now() - timedelta(hours=1)
        many_hours_ago = an_hour_ago - timedelta(hours=999)
        self.article_data_list = [
            {'title': 'foo',
             'status': 'vor',
             'version': 1,
             'doi': "10.7554/eLife.00001",
             'journal': self.journal,
             'datetime_published': an_hour_ago,
            },
            
            {'title': 'bar',
             'status': 'vor',
             'version': 1,
             'doi': "10.7554/eLife.00002",
             'journal': self.journal,
             'datetime_published': many_hours_ago, # **
            },

            {'title': 'baz',
             'version': 1,
             'status': 'poa', # **
             'doi': "10.7554/eLife.00003",
             'journal': self.journal,
             'datetime_published': an_hour_ago,
             }
        ]
        [logic.add_or_update_article(**article_data) for article_data in self.article_data_list]        


    def tearDown(self):
        pass

    def test_specific_feed_single_article(self):
        """a specific article can be targeted in the rss. why? spot fixes
        to ALM and a person may be interested in future versions of a given article"""
        doi = self.article_data_list[0]['doi']
        aid = doi[8:]
        url = reverse('rss-specific-article-list', kwargs={'aid_list': aid})
        resp = self.c.get(url)
        self.assertEqual(1, len(re.findall('<guid', resp.content)))
    
    def test_specific_feed_many_article(self):
        """a specific article can be targeted in the rss. why? spot fixes
        to ALM and a person may be interested in future versions of a given article"""
        aid_list = map(lambda a: a['doi'][8:], self.article_data_list)
        aid_str = ','.join(aid_list)
        url = reverse('rss-specific-article-list', kwargs={'aid_list': aid_str})
        resp = self.c.get(url)
        self.assertEqual(3, len(re.findall('<guid', resp.content)))

    def test_last_n_articles(self):
        url = reverse('rss-recent-article-list', kwargs={'article_types': 'vor', 'since': '1'})
        resp = self.c.get(url)
        self.assertEqual(1, len(re.findall('<guid', resp.content)))
