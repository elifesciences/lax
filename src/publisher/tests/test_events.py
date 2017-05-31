from . import base
from os.path import join
from publisher import models, ajson_ingestor
from unittest.mock import patch

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
        expected_events = [
            models.DATETIME_ACTION_INGEST,
        ]
        ajson_ingestor.ingest(self.without_history)
        ael = models.ArticleEvent.objects.all()
        self.assertEqual(ael.count(), len(expected_events))


class Two(base.TransactionBaseCase):
    def setUp(self):
        self.f1 = join(self.fixture_dir, 'ajson', 'elife-10627-v1.xml.json')
        self.ajson1 = self.load_ajson(self.f1, strip_relations=False)

        self.f2 = join(self.fixture_dir, 'ajson', 'elife-09560-v1.xml.json')
        self.ajson2 = self.load_ajson(self.f2, strip_relations=False)

        self.commits = 0

    def tearDown(self):
        pass

    @patch('publisher.ajson_ingestor.aws_events.notify')
    def test_related_events(self, notify_mock):
        "aws_events.notify is called once for the article being ingested and once each for related articles"

        ajson_ingestor.ingest(self.ajson1) # has 2 related

        def event_msid(index):
            args, first_arg = 1, 0
            return notify_mock.mock_calls[index][args][first_arg].manuscript_id

        # 10627 has two relations, 9561 and 9560
        # ensure `notify` called once for each article
        self.assertEqual(len(notify_mock.mock_calls), 3)

        # ensure the events have the right manuscript id
        # internal relationships, lowest to highest msid
        self.assertEqual(event_msid(1), 9560)
        self.assertEqual(event_msid(2), 9561)


    def test_related_events2(self):
        """aws_events.notify is called once for the article being ingested and once
        each for related articles, including reverse relations"""

        ajson_ingestor.ingest(self.ajson1) # has 2 related, 9561 and 9560

        with patch('publisher.ajson_ingestor.aws_events.notify') as notify_mock:

            def event_msid(index):
                args, first_arg = 1, 0
                return notify_mock.mock_calls[index][args][first_arg].manuscript_id

            ajson_ingestor.ingest(self.ajson2) # has 2 related, 10627, 9561

            self.assertEqual(len(notify_mock.mock_calls), 3)

            # ensure the events have the right manuscript id
            self.assertEqual(event_msid(0), 9560)
            # internal relationships, lowest to highest msid
            self.assertEqual(event_msid(1), 9561) # linked by 9560
            self.assertEqual(event_msid(2), 10627) # links to 9560
