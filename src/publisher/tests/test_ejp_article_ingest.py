from . import base
from os.path import join
from publisher import logic, models, ejp_ingestor
from dateutil import parser

def parse(v):
    return parser.parse(v).date()

class TestEJPIngest(base.BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        self.partial_json_path = join(self.fixture_dir, 'partial-ejp-to-lax-report.json')
        self.tiny_json_path = join(self.fixture_dir, 'tiny-ejp-to-lax-report.json')

    def tearDown(self):
        pass

    def test_ejp_ingest(self):
        self.assertEqual(models.Article.objects.count(), 0)
        ejp_ingestor.import_article_list_from_json_path(self.journal, self.partial_json_path)
        self.assertEqual(models.Article.objects.count(), 748)

    def test_ejp_ingest_with_nocreate(self):
        "ensure ejp ingest doesn't create articles if we've told it not to"
        data = {"manuscript_id": 123}
        self.assertRaises(models.Article.DoesNotExist, ejp_ingestor.import_article, self.journal, data, create=False)
        
    def test_ejp_ingest_data(self):
        ejp_ingestor.import_article_list_from_json_path(self.journal, self.tiny_json_path)
        self.assertEqual(models.Article.objects.count(), 6)
        art = models.Article.objects.get(manuscript_id=11835)
        expected_data = {
            "manuscript_id": 11835, 
            "ejp_type": "RA",
            "date_initial_qc": parse("2015-09-24T00:00:00"), 
            "date_initial_decision": parse("2015-10-05T00:00:00"), 
            "initial_decision": "EF", 
            "date_full_qc": parse("2015-10-23T00:00:00"), 
            "date_full_decision": parse("2015-11-16T00:00:00"), 
            "decision": "RVF", 
            "date_rev1_qc": parse("2016-02-23T00:00:00"), 
            "date_rev1_decision": parse("2016-02-24T00:00:00"), 
            "rev1_decision": "RVF", 
            "date_rev2_qc": parse("2016-03-08T00:00:00"), 
            "date_rev2_decision": parse("2016-03-14T00:00:00"), 
            "rev2_decision": "AF", 
            "date_rev3_qc": None, 
            "date_rev3_decision": None, 
            "rev3_decision": None, 
            "date_rev4_qc": None, 
            "date_rev4_decision": None, 
            "rev4_decision": None
        }
        for key, val in expected_data.items():
            self.assertEqual(getattr(art, key), val)

    def test_ejp_ingest_over_existing_data_with_defaults(self):
        "importing ejp articles over existing articles causes an error"
        self.assertEqual(models.Article.objects.count(), 0)
        article_data_list = [
            {'manuscript_id': 123,
             'journal': self.journal},
             
            {'manuscript_id': 11835,
             'journal': self.journal},

            {'manuscript_id': 321,
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        self.assertEqual(models.Article.objects.count(), 3)
        self.assertRaises(AssertionError, ejp_ingestor.import_article_list_from_json_path, self.journal, self.tiny_json_path)
        self.assertEqual(models.Article.objects.count(), 3) # import is atomic, all or nothing.
        
    def test_ejp_ingest_over_existing_data(self):
        "importing ejp articles and updating existing articles is possible but only if we explicitly say so"
        self.assertEqual(models.Article.objects.count(), 0)
        article_data_list = [
            {'manuscript_id': 123,
             'journal': self.journal},
             
            {'manuscript_id': 11835,
             'journal': self.journal},

            {'manuscript_id': 321,
             'journal': self.journal},
        ]
        [logic.add_or_update_article(**article_data) for article_data in article_data_list]
        self.assertEqual(models.Article.objects.count(), 3)
        ejp_ingestor.import_article_list_from_json_path(self.journal, self.tiny_json_path, update=True)
        self.assertEqual(models.Article.objects.count(), 8)
        art = models.Article.objects.get(manuscript_id=11835)
        self.assertTrue(art.initial_decision)
