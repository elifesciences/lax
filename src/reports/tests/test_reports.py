from unittest.mock import patch
import re
from os.path import join
from publisher.tests import base
from publisher import logic as publogic, utils, ajson_ingestor, models
from reports import logic
import xml.etree.ElementTree as ET
from django.test import Client
from django.core.urlresolvers import reverse

class CMD1(base.BaseCase):
    def setUp(self):
        self.nom = 'report'
        f1 = join(self.fixture_dir, 'ajson', 'elife-20105-v1.xml.json')
        self.ajson = self.load_ajson(f1)
        self.msid = 20105
        self.version = 1

    def tearDown(self):
        pass

    def test_cmd1(self):
        """valid article-json is successfully ingested, creating an article,
        an article version and storing the ingestion request"""
        ajson_ingestor.ingest(self.ajson)

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

    @patch('reports.management.commands.report.LOG')
    def test_cmd1_bad_vals(self, mock):
        "correct csv is still written despite bad location data"
        # give article location a horrible value
        horrible_very_bad_value = """'foo'o"ooo"o'"\"\';,oobarpants"""
        self.ajson['article']['-meta']['location'] = horrible_very_bad_value
        ajson_ingestor.ingest(self.ajson)

        args = [self.nom, 'all-article-versions-as-csv']

        retcode, stdout = self.call_command(*args)
        self.assertEqual(retcode, 0)

        rows = stdout.splitlines()
        self.assertEqual(len(rows), 1) # 1 article, 1 row

        row = rows[0]
        bits = row.split(',')
        # this naive split of a properly encoded csv-escaped value isn't going to work here
        # self.assertEqual(len(bits), 3) # 3 bits to a row
        # and consumers will probably choke on this bad data. ensure a warning is emitted
        self.assertTrue(mock.warn.called_once())

        # msid
        self.assertEqual(int(bits[0]), self.msid)

        # version
        self.assertTrue(bits[1], self.version)

        # location
        self.assertTrue(bits[2], horrible_very_bad_value)


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

    def test_paw_recent_report_data2(self):
        "recent report returns the earliest vor version of every article version"
        # we have no articles with a POA and two VORs
        # but we do have on with two POAs and one VOR
        # so lets convert a POA for some variety
        models.ArticleVersion.objects.filter(article__manuscript_id=6250, version=2).update(status=models.VOR)

        # msid, earliest vor, latest vor
        cases = [
            (353, 1, 1), (385, 1, 1),
            (1328, 1, 1), (2619, 1, 1),
            (3401, 3, 3), (3665, 1, 1),
            (6250, 2, 3), # altered
            (7301, 1, 1), (8025, 2, 2)
        ]

        results = logic.paw_recent_report_raw_data(limit=None)
        for msid, earliest_vor, latest_vor in cases:
            av = results.get(article__manuscript_id=msid, version=earliest_vor)
            self.assertEqual(av.article.latest_version.version, latest_vor)

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

    def test_paw_recent_report_date_updated(self):
        # we have no articles with a POA and two VORs
        # but we do have on with two POAs and one VOR
        # so lets convert a POA
        models.ArticleVersion.objects.filter(article__manuscript_id=6250, version=2).update(status=models.VOR)

        # and give our targets a predictable date
        dummy1 = '2018-01-01T00:00:00Z'
        dummy2 = '2018-02-01T00:00:00Z'
        models.ArticleVersion.objects.filter(article__manuscript_id=6250, version=2).update(datetime_published=dummy1)
        models.ArticleVersion.objects.filter(article__manuscript_id=6250, version=3).update(datetime_published=dummy2)

        # fetch the xml
        resp = Client().get(reverse('paw-recent-report', kwargs={'days_ago': 9999}))
        self.assertEqual(resp.status_code, 200)
        xml = resp.content.decode('utf-8')

        # we should have ONE item with two dates
        root = ET.fromstring(xml)
        item = root.find("./channel/item[guid='https://dx.doi.org/10.7554/eLife.06250']")
        cases = [
            # dc:date.latest is the most recent VOR pubdate
            ("{http://purl.org/dc/elements/1.1/}date.latest", dummy2),
            # dc:date is the earliest VOR pubdate
            ("{http://purl.org/dc/elements/1.1/}date", dummy1),
        ]
        for path, expected in cases:
            actual = item.find(path).text
            self.assertEqual(actual, expected, "expecting {0} for path {1} got {2}".format(expected, path, actual))
