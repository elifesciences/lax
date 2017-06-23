import re
from os.path import join
from publisher.tests import base
from publisher import logic as publogic, utils, ajson_ingestor, models
from reports import logic

from django.test import Client
from django.core.urlresolvers import reverse

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
            fname = "elife-%s.xml.json" % fname
            path = join(self.fixture_dir, 'ppp2', fname)
            ajson_ingestor.ingest_publish(self.load_ajson(path)) # strip relations

        # we need to coerce the data of the non-v1 articles a little
        # as we removed the eif ingestor that bypassed business logic
        cases = [
            # vor
            (3401, 3, "2014-08-01"),
            (8025, 2, "2015-06-16"),
        ]
        for msid, ver, dtstr in cases:
            av = models.ArticleVersion.objects.get(article__manuscript_id=msid, version=ver)
            av.datetime_published = utils.todt(dtstr)
            av.save()

        self.vor_version_count = 9
        self.poa_version_count = 6

        self.poa_art_count = 1
        self.vor_art_count = 9

    def tearDown(self):
        pass

    def test_paw_recent_report_data(self):
        res = logic.paw_recent_report_raw_data(limit=None)
        self.assertEqual(res.count(), self.vor_art_count)
        vor_cases = [
            (353, 1, "2012-12-13"), # v1 'pub-date' dates
            (3401, 3, "2014-08-01"), # >v1 'update' dates
            (8025, 2, "2015-06-16"),
        ]
        for msid, expected_version, expected_pubdate in vor_cases:
            av = res.get(article__manuscript_id=msid)
            self.assertEqual(av.status, 'vor')
            self.assertEqual(av.version, expected_version)
            self.assertEqual(utils.ymd(av.datetime_published), expected_pubdate)

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
