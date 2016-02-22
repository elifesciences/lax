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

    def tearDown(self):
        pass

    def test_last_n_articles(self):
        an_hour_ago = datetime.now() - timedelta(hours=1)
        many_hours_ago = an_hour_ago - timedelta(hours=999)
        article_data_list = [
            {'title': 'foo',
             'status': 'vor',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY",
             'journal': self.journal,
             'datetime_published': an_hour_ago,
            },
            
            {'title': 'bar',
             'status': 'vor',
             'version': 1,
             'doi': "10.7554/eLife.DUMMY1",
             'journal': self.journal,
             'datetime_published': many_hours_ago, # **
            },

            {'title': 'baz',
             'version': 1,
             'status': 'poa', # **
             'doi': "10.7554/eLife.DUMMY2",
             'journal': self.journal,
             'datetime_published': an_hour_ago,
             }
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]        
        url = reverse('rss-articles', kwargs={'article_types': 'vor', 'since': 'today'})
        resp = self.c.get(url)
        print resp.content
        self.assertEqual(1, len(re.findall('<guid', resp.content)))
        self.assertTrue(False)
