import re
from . import base
from django.test import Client
from django.core.urlresolvers import reverse
from publisher import logic, models, utils
from datetime import timedelta
from unittest import skip


class TestLatest(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_only_most_recent_article_versions_returned(self):
        an_hour_ago = utils.utcnow() - timedelta(hours=1)
        many_hours_ago = an_hour_ago - timedelta(hours=999)
        fmt = utils.ymdhms
        article_data_list = [
            {
                "title": "foo",
                "version": 1,
                "doi": "10.7554/eLife.00001",
                "pub-date": fmt(an_hour_ago),
            },
            {
                "title": "bar",
                "version": 1,
                "doi": "10.7554/eLife.00002",
                "pub-date": fmt(many_hours_ago),
            },
            {
                "title": "bar",
                "version": 2,
                "doi": "10.7554/eLife.00002",
                "pub-date": fmt(many_hours_ago - timedelta(hours=1)),
                "update": fmt(many_hours_ago - timedelta(hours=1)),
            },
            {
                "title": "bar",
                "version": 3,
                "doi": "10.7554/eLife.00002",
                "pub-date": fmt(many_hours_ago - timedelta(hours=2)),
                "update": fmt(many_hours_ago - timedelta(hours=2)),
            },
            {
                "title": "baz",
                "version": 1,
                "doi": "10.7554/eLife.00003",
                "pub-date": fmt(an_hour_ago + timedelta(minutes=5)),
            },
            {
                "title": "baz",
                "version": 2,
                "doi": "10.7554/eLife.00003",
                "pub-date": fmt(an_hour_ago + timedelta(minutes=10)),
                "update": fmt(an_hour_ago + timedelta(minutes=10)),
            },
        ]
        [
            self.add_or_update_article(**article_data)
            for article_data in article_data_list
        ]

        self.assertEqual(models.Article.objects.count(), 3)
        self.assertEqual(models.ArticleVersion.objects.count(), 6)

        total, avlist = logic.latest_article_version_list()
        self.assertEqual(total, 3)
        self.assertEqual(len(avlist), 3)

        expected_version_order = [
            ("10.7554/eLife.00003", 2),  # published less than an hour ago
            ("10.7554/eLife.00001", 1),  # published an hour ago
            ("10.7554/eLife.00002", 3),  # published many hours ago
        ]

        for av, expected in zip(avlist, expected_version_order):
            self.assertEqual(av.article.doi, expected[0])
            self.assertEqual(av.version, expected[1])


class RSSViews(base.BaseCase):
    def setUp(self):
        self.c = Client()
        an_hour_ago = utils.utcnow() - timedelta(hours=1)
        many_hours_ago = an_hour_ago - timedelta(hours=999)
        fmt = utils.ymdhms
        self.article_data_list = [
            {
                "title": "foo",
                "status": "vor",
                "version": 1,
                "doi": "10.7554/eLife.00001",
                "pub-date": fmt(an_hour_ago),
            },
            {
                "title": "bar",
                "status": "vor",
                "version": 1,
                "doi": "10.7554/eLife.00002",
                "pub-date": fmt(many_hours_ago),
            },
            {
                "title": "baz",
                "version": 1,
                "status": "poa",  # **
                "doi": "10.7554/eLife.00003",
                "pub-date": fmt(an_hour_ago),
            },
        ]
        [
            self.add_or_update_article(**article_data)
            for article_data in self.article_data_list
        ]

    def tearDown(self):
        pass

    def test_specific_feed_single_article(self):
        """a specific article can be targeted in the rss. why? spot fixes
        to ALM and a person may be interested in future versions of a given article"""
        doi = self.article_data_list[0]["doi"]
        aid = doi[8:]
        url = reverse("rss-specific-article-list", kwargs={"aid_list": aid})
        resp = self.c.get(url)
        self.assertEqual(1, len(re.findall("<guid", resp.content.decode("utf-8"))))

    @skip("nobody uses rss. tune performance then")
    def test_specific_feed_single_article_db_performance(self):
        doi = self.article_data_list[0]["doi"]
        aid = doi[8:]
        url = reverse("rss-specific-article-list", kwargs={"aid_list": aid})
        with self.assertNumQueries(1):
            self.c.get(url)

    @skip("nobody uses rss. tune performance then")
    def test_specific_feed_many_article(self):
        """a specific article can be targeted in the rss. why? spot fixes
        to ALM and a person may be interested in future versions of a given article"""
        aid_list = [a["doi"][8:] for a in self.article_data_list]
        aid_str = ",".join(aid_list)
        url = reverse("rss-specific-article-list", kwargs={"aid_list": aid_str})
        resp = self.c.get(url)
        self.assertEqual(3, len(re.findall("<guid", resp.content.decode("utf-8"))))

    @skip("nobody uses rss. tune performance then")
    def test_specific_feed_many_article_db_performance(self):
        "we hit the database once for an rss feed even with 'many' article versions in the system"
        aid_list = [a["doi"][8:] for a in self.article_data_list]
        aid_str = ",".join(aid_list)
        url = reverse("rss-specific-article-list", kwargs={"aid_list": aid_str})
        with self.assertNumQueries(1):
            self.c.get(url)

    def test_last_n_articles(self):
        url = reverse(
            "rss-recent-article-list", kwargs={"article_status": "vor", "since": "1"}
        )
        resp = self.c.get(url)
        self.assertEqual(1, len(re.findall("<guid", resp.content.decode("utf-8"))))

    @skip("nobody uses rss. tune performance then")
    def test_last_n_articles_db_performance(self):
        url = reverse(
            "rss-recent-article-list", kwargs={"article_status": "vor", "since": "999"}
        )
        with self.assertNumQueries(1):
            self.c.get(url)
