import re
from os.path import join
from . import base
from publisher import ingestor, logic, models, reports, utils
from django.test import Client
from django.core.urlresolvers import reverse

class TestReport(base.BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        import_all = [
            '00353.1', # discussion
            '00385.1', # commentary
            '01328.1', # correction
            '02619.1', # editorial
            '03401.1', # research
            '03401.2', 
            '03401.3',
            '03665.1', # research
            '06250.1', # research
            '06250.2',
            '06250.3',
            '07301.1', # research
            '08025.1', # research
            '08025.2',
        ]
        for subdir in import_all:
            fname = subdir.replace('.', '-v')
            fname = "elife-%s.json" % fname
            path = join(self.fixture_dir, 'ppp', subdir, fname)
            ingestor.import_article_from_json_path(self.journal, path)

    def tearDown(self):
        pass

    def test_poa_vor_pubdates_data(self):
        "the report yields the expected data in the expected format"
        self.assertEqual(models.Article.objects.count(), 9)
        self.assertEqual(models.ArticleVersion.objects.count(), 14)
        report = reports.article_poa_vor_pubdates()
        report = list(report) # result is lazy, force evaluation here
        #self.assertEqual(len(report), 9) # most (all?) non-research articles are being excluded
        self.assertEqual(len(report), 5)
        for row in report:
            self.assertEqual(len(row), 3)

    def test_paw_article_data_poa(self):
        data = list(reports.paw_article_data())
        expected_keys = [
            'title', 'link', 'description', 'author', 'category-list',
            'guid', 'pub-date', 'update-date'
        ]
        self.assertEqual(len(data), 9)
        for row in data:
            try:
                self.assertTrue(utils.has_all_keys(row, expected_keys))
            except AssertionError:
                print 'expecting',expected_keys
                print 'got keys',row.keys()
                raise

    #
    # views
    #
            
    def test_poa_vor_pubdates_report_api(self):
        url = reverse('poa-vor-pubdates')
        resp = Client().get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'text/csv')
            
    def test_paw_article_data_rss_view(self):
        url = reverse('paw-article-data')
        resp = Client().get(url)
        self.assertEqual(resp.status_code, 200)
        xml = resp.content
        self.assertEqual(len(re.findall('<item>', xml)), 9)

        # assert the 'pubdate' is actually the updated date
        self.assertTrue(False)
