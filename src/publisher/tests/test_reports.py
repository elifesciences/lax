import re
from os.path import join
from . import base
from publisher import eif_ingestor, logic, models, reports, utils
from django.test import Client
from unittest import skip
from django.core.urlresolvers import reverse

class TestReport(base.BaseCase):
    def setUp(self):
        self.journal = logic.journal()
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

    def test_poa_vor_pubdates_data(self):
        "the report yields the expected data in the expected format"
        self.assertEqual(models.Article.objects.count(), 10)
        self.assertEqual(models.ArticleVersion.objects.count(), 15)
        report = reports.article_poa_vor_pubdates()
        report = list(report) # result is lazy, force evaluation here
        #self.assertEqual(len(report), 9) # most (all?) non-research articles are being excluded
        self.assertEqual(len(report), self.research_art_count)
        for row in report:
            self.assertEqual(len(row), 3)

    @skip("paw_article_data() now returns a queryset not a lazy list of rows")
    def test_paw_report_data(self):
        "the data is in the structure we expect"
        data = list(reports.paw_article_data())
        expected_keys = [
            'title', 'link', 'description', 'author', 'category-list',
            'guid', 'pub-date', 'transition-date'
        ]
        expected_art_count = self.poa_art_count + self.vor_art_count
        self.assertEqual(len(data), expected_art_count)
        for row in data:
            try:
                self.assertTrue(utils.has_all_keys(row, expected_keys))
            except AssertionError:
                print 'expecting',expected_keys
                print 'got keys',row.keys()
                raise

    def test_paw_recent_report_data(self):
        res = reports.paw_recent_report_raw_data(limit=None)
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
        res = reports.paw_ahead_report_raw_data(limit=None)
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
            
    def test_poa_vor_pubdates_report_api(self):
        url = reverse('poa-vor-pubdates')
        resp = Client().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')

    def test_paw_recent_report(self):
        url = reverse('paw-recent-report', kwargs={'days_ago': 9999})
        resp = Client().get(url)
        self.assertEqual(resp.status_code, 200)
        xml = resp.content
        print 'xml:',xml
        self.assertEqual(len(re.findall('<item>', xml)), self.vor_art_count)
        
    def test_paw_ahead_report(self):
        url = reverse('paw-ahead-report', kwargs={'days_ago': 9999})
        resp = Client().get(url)
        self.assertEqual(resp.status_code, 200)
        xml = resp.content
        self.assertEqual(len(re.findall('<item>', xml)), self.poa_art_count)
