from . import base
from os.path import join
from publisher import logic, models, ejp_ingestor, utils
from dateutil import parser


def parse(v):
    return parser.parse(v).date()


class EJPIngest(base.BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        self.partial_json_path = join(
            self.fixture_dir, "partial-ejp-to-lax-report.json"
        )
        self.tiny_json_path = join(self.fixture_dir, "tiny-ejp-to-lax-report.json")

    def tearDown(self):
        pass

    def test_ejp_ingest(self):
        self.assertEqual(models.Article.objects.count(), 0)
        ejp_ingestor.import_article_list_from_json_path(
            self.journal, self.partial_json_path
        )
        self.assertEqual(models.Article.objects.count(), 748)

    def test_ejp_ingest_with_nocreate(self):
        "ensure ejp ingest doesn't create articles if we've told it not to"
        data = {"manuscript_id": 123}
        self.assertEqual(models.Article.objects.count(), 0)
        ejp_ingestor.import_article(self.journal, data, create=False)
        self.assertEqual(models.Article.objects.count(), 0)

    def test_ejp_ingest_data(self):
        ejp_ingestor.import_article_list_from_json_path(
            self.journal, self.tiny_json_path
        )
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
            "rev4_decision": None,
        }
        for key, val in expected_data.items():
            self.assertEqual(getattr(art, key), val)

    def test_ejp_ingest_over_existing_data_with_defaults(self):
        "importing EJP stubs over existing articles isn't possible by default"
        self.assertEqual(0, models.Article.objects.count())

        # does not exist in import
        art1 = {
            "journal": self.journal,
            "manuscript_id": 123,
            "doi": "10.7554/eLife.000123",
        }
        # exists in ejp import
        art2 = {
            "journal": self.journal,
            "manuscript_id": 11835,
            "doi": "10.7554/eLife.11835",
            "ejp_type": "FOO",
        }
        # does not exist in ejp import
        art3 = {
            "journal": self.journal,
            "manuscript_id": 321,
            "doi": "10.7554/eLife.000321",
        }

        for art in [art1, art2, art3]:
            utils.create_or_update(
                models.Article, art, ["manuscript_id", "journal"], update=False
            )
        self.assertEqual(3, models.Article.objects.count())

        # attempt to import 6 new articles.
        # 1 of the 6 already exists and will not be updated with data from the import
        ejp_ingestor.import_article_list_from_json_path(
            self.journal, self.tiny_json_path
        )

        # there should now be the original 3 articles after import + 5 new ones
        self.assertEqual(8, models.Article.objects.count())

        # and the overlapping article should *not* have been modified
        self.assertEqual(
            "FOO", models.Article.objects.get(manuscript_id=11835).ejp_type
        )

    def test_ejp_ingest_over_existing_data(self):
        "importing EJP stubs over existing articles isn't possible by default, unless `update` is explicitly set to `True`"
        self.assertEqual(models.Article.objects.count(), 0)

        # does not exist in import
        art1 = {
            "journal": self.journal,
            "manuscript_id": 123,
            "doi": "10.7554/eLife.000123",
        }
        # exists in ejp import
        art2 = {
            "journal": self.journal,
            "manuscript_id": 11835,
            "doi": "10.7554/eLife.11835",
            "ejp_type": "FOO",
        }
        # does not exist in ejp import
        art3 = {
            "journal": self.journal,
            "manuscript_id": 321,
            "doi": "10.7554/eLife.000321",
        }

        for art in [art1, art2, art3]:
            utils.create_or_update(
                models.Article, art, ["manuscript_id", "journal"], update=False
            )
        self.assertEqual(3, models.Article.objects.count())

        # attempt to import 6 new articles.
        # 1 of the 6 already exists and will be updated with data from the import
        ejp_ingestor.import_article_list_from_json_path(
            self.journal, self.tiny_json_path, update=True
        )

        # there should now be the original 3 articles after import + 5 new ones
        self.assertEqual(8, models.Article.objects.count())

        # and the overlapping article should have modified the original article
        updated_article = models.Article.objects.get(manuscript_id=11835)
        self.assertEqual("RA", updated_article.ejp_type)
        self.assertTrue(updated_article.initial_decision)
