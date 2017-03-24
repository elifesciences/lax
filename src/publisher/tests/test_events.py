from .base import BaseCase
from os.path import join
from publisher import models, ajson_ingestor

class One(BaseCase):
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
        expected_events = [
            models.DATETIME_ACTION_INGEST,
        ]
        ajson_ingestor.ingest(self.without_history)
        ael = models.ArticleEvent.objects.all()
        self.assertEqual(ael.count(), len(expected_events))
