import json
from . import base
from os.path import join
from publisher import logic, models, ajson_ingestor, ejp_ingestor

class EJP(base.BaseCase):
    def setUp(self):
        self.journal = logic.journal()

        self.stub = json.loads('''{
            "manuscript_id": "11384",
            "ejp_type": "TR",

            "date_initial_qc": "2015-09-03T00:00:00",
            "date_initial_decision": "2015-09-06T00:00:00",
            "initial_decision": "EF",

            "date_full_qc": "2015-09-09T00:00:00",
            "date_full_decision": "2015-10-02T00:00:00",
            "decision": "RVF",

            "date_rev1_qc": "2015-11-20T00:00:00",
            "date_rev1_decision": "2015-11-24T00:00:00",
            "rev1_decision": "RVF",

            "date_rev2_qc": "2015-12-14T00:00:00",
            "date_rev2_decision": "2015-12-16T00:00:00",
            "rev2_decision": "AF",

            "date_rev3_qc": null,
            "date_rev3_decision": null,
            "rev3_decision": null,
            "date_rev4_qc": null,
            "date_rev4_decision": null,
            "rev4_decision": null
        }''', object_pairs_hook=ejp_ingestor.load_with_datetime)

    def tearDown(self):
        pass

    def test_ejp_ingest_events(self):
        "ensure a single ejp ingest does exactly as we expect"
        self.assertEqual(models.ArticleEvent.objects.count(), 0)
        ejp_ingestor.import_article(self.journal, self.stub)
        #[print(x.datetime_event, x.event, x.value) for x in models.ArticleEvent.objects.all()]
        # 2xinitial, 2xfull, 2xrev1, 2xrev2
        self.assertEqual(models.ArticleEvent.objects.count(), 8)
        # todo: test data

    def test_many_ejp_ingest_events(self):
        "run a huge list of ejp article data"
        fixture = join(self.fixture_dir, 'partial-ejp-to-lax-report.json')
        ejp_ingestor.import_article_list_from_json_path(self.journal, fixture)
        expected_events = 2208
        self.assertEqual(models.ArticleEvent.objects.count(), expected_events)

class One(base.BaseCase):
    def setUp(self):
        f1 = join(self.fixture_dir, 'ajson', 'elife-01968-v1.xml.json')
        self.without_history = self.load_ajson(f1)

        f2 = join(self.fixture_dir, 'ajson', 'elife-20105-v1.xml.json')
        self.with_history = self.load_ajson(f2)

    def tearDown(self):
        pass

    def test_ingest_creates_events(self):
        expected_events = [
            models.DATE_XML_RECEIVED,
            models.DATE_XML_ACCEPTED,
            models.DATETIME_ACTION_INGEST,
        ]
        ajson_ingestor.ingest(self.with_history)
        ael = models.ArticleEvent.objects.all()
        self.assertEqual(ael.count(), len(expected_events))

        # order should be preserved
        for event_type, event_obj in zip(expected_events, ael):
            self.assertEqual(event_obj.event, event_type)
            if event_type == models.DATETIME_ACTION_INGEST:
                self.assertEqual(event_obj.value, "forced=False")

    def test_publish_creates_events(self):
        expected_events = [
            models.DATE_XML_RECEIVED,
            models.DATE_XML_ACCEPTED,
            models.DATETIME_ACTION_INGEST,
            models.DATETIME_ACTION_PUBLISH,
        ]
        ajson_ingestor.ingest_publish(self.with_history)
        ael = models.ArticleEvent.objects.all()
        self.assertEqual(ael.count(), len(expected_events))

        # order should be preserved
        for event_type, event_obj in zip(expected_events, ael):
            self.assertEqual(event_obj.event, event_type)
            if event_type == models.DATETIME_ACTION_PUBLISH:
                self.assertEqual(event_obj.value, "forced=False")

    def test_ingest_events_no_history(self):
        "when article xml has no accepted or received dates, events won't be created for them"
        expected_events = [
            models.DATETIME_ACTION_INGEST,
        ]
        ajson_ingestor.ingest(self.without_history)
        ael = models.ArticleEvent.objects.all()
        self.assertEqual(ael.count(), len(expected_events))
