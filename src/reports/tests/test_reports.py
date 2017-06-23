import re
from os.path import join
from publisher.tests import base
from publisher import eif_ingestor, logic as publogic, utils, ajson_ingestor, models
from reports import logic

from django.test import Client
from django.core.urlresolvers import reverse

class CMD1(base.BaseCase):
    def setUp(self):
        self.nom = 'report'
        f1 = join(self.fixture_dir, 'ajson', 'elife-20105-v1.xml.json')
        self.ajson = self.load_ajson(f1)
        self.msid = 20105
        self.version = 1
        ajson_ingestor.ingest(self.ajson)

    def tearDown(self):
        pass

    def test_cmd1(self):
        """valid article-json is successfully ingested, creating an article,
        an article version and storing the ingestion request"""
        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)

        args = [self.nom, 'all-article-versions-as-csv']
        retcode, stdout = self.call_command(*args)
        self.assertEqual(retcode, 0)
        rows = stdout.splitlines()
        self.assertEqual(len(rows), 1) # 1 article, 1 row

        row = rows[0]
        bits = row.split(',')
        self.assertEqual(len(bits), 3) # 3 bits to a row

        # msid
        self.assertEqual(int(bits[0]), self.msid)

        # version
        self.assertTrue(bits[1], self.version)

        # location
        expected_loc = "https://raw.githubusercontent.com/elifesciences/elife-article-xml/694f91de44ebc7cc61aba8be0982b7613cac8c3f/articles/elife-20105-v1.xml"
        self.assertTrue(bits[2], expected_loc)


class TestReport(base.BaseCase):
    def setUp(self):
        self.journal = publogic.journal()
        import_all = [
            '00353.1', # discussion, VOR

            '00385.1', # commentary, VOR

            '01328.1', # correction, VOR

            '02619.1', # editorial, VOR

            '03401.1', # research, POA
            '03401.2', # POA
            '03401.3', # VOR

            '03665.1', # research, VOR

            '06250.1', # research, POA
            '06250.2', # POA
            '06250.3', # VOR

            '07301.1', # research, VOR

            '08025.1', # research, POA
            '08025.2', # VOR

            '09571.1', # research, POA
        ]
        for subdir in import_all:
            fname = subdir.replace('.', '-v')
            fname = "elife-%s.json" % fname
            path = join(self.fixture_dir, 'ppp', subdir, fname)
            eif_ingestor.import_article_from_json_path(self.journal, path)

        self.vor_version_count = 9
        self.poa_version_count = 6

        self.poa_art_count = 1
        self.vor_art_count = 9

        self.research_art_count = 6

    def tearDown(self):
        pass

    def test_paw_recent_report_data(self):
        res = logic.paw_recent_report_raw_data(limit=None)
        self.assertEqual(res.count(), self.vor_art_count)
        cases = [
            ("00353", 1, "2012-12-13"), # v1 'pub-date' dates
            ("03401", 3, "2014-08-01"), # >v1 'update' dates
            ("08025", 2, "2015-06-16"),
        ]
        for msid, expected_version, expected_pubdate in cases:
            o = res.get(article__doi='10.7554/eLife.' + msid)
            self.assertEqual(o.status, 'vor')
            self.assertEqual(o.version, expected_version)
            self.assertEqual(utils.ymd(o.datetime_published), expected_pubdate)

    def test_paw_ahead_report_data(self):
        res = logic.paw_ahead_report_raw_data(limit=None)
        self.assertEqual(res.count(), self.poa_art_count)
        cases = [
            ("09571", 1, "2015-11-09")
        ]
        for msid, expected_version, expected_pubdate in cases:
            o = res.get(article__doi='10.7554/eLife.' + msid)
            self.assertEqual(o.status, 'poa')
            self.assertEqual(o.version, expected_version)
            self.assertEqual(utils.ymd(o.datetime_published), expected_pubdate)

    #
    # views
    #

    def test_paw_recent_report(self):
        url = reverse('paw-recent-report', kwargs={'days_ago': 9999})
        resp = Client().get(url)
        self.assertEqual(resp.status_code, 200)
        xml = resp.content.decode('utf-8')
        self.assertEqual(len(re.findall('<item>', xml)), self.vor_art_count)

    def test_paw_ahead_report(self):
        url = reverse('paw-ahead-report', kwargs={'days_ago': 9999})
        resp = Client().get(url)
        self.assertEqual(resp.status_code, 200)
        xml = resp.content.decode('utf-8')
        self.assertEqual(len(re.findall('<item>', xml)), self.poa_art_count)
