from os.path import join
from . import base
from publisher import ingestor, logic, models, reports

class TestReport(base.BaseCase):
    def setUp(self):
        self.journal = logic.journal()

    def tearDown(self):
        pass

    def test_poa_vor_pubdates_report(self):
        "the report yields the expected data in the expected format"
        import_all = [
            '00353.1',
            '00385.1',
            '01328.1',
            '02619.1',
            '03401.1',
            '03401.2',
            '03401.3',
            '03665.1',
            '06250.1',
            '06250.2',
            '06250.3',
            '07301.1',
            '08025.1',
            '08025.2',
        ]
        for subdir in import_all:
            fname = subdir.replace('.', '-v')
            fname = "elife-%s.json" % fname
            path = join(self.fixture_dir, 'ppp', subdir, fname)
            ingestor.import_article_from_json_path(self.journal, path)
        self.assertEqual(models.Article.objects.count(), 9)
        self.assertEqual(models.ArticleVersion.objects.count(), len(import_all))
        report = reports.article_poa_vor_pubdates()
        report = list(report) # result is lazy, force evaluation here

        self.assertEqual(len(report), 9)
        for row in report:
            self.assertEqual(len(row), 3)
        
