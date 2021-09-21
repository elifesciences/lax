from . import base
from os.path import join
from publisher import models, ajson_ingestor
from unittest.mock import patch
from datetime import datetime
import pytz


class One(base.BaseCase):
    def setUp(self):
        f1 = join(self.fixture_dir, "ajson", "elife-01968-v1.xml.json")
        self.without_history = self.load_ajson(f1)

        f2 = join(self.fixture_dir, "ajson", "elife-20105-v1.xml.json")
        self.with_history = self.load_ajson(f2)

    def test_ingest_events_no_history(self):
        "when article xml has no accepted or received dates, events won't be created for them"
        expected_events = [models.DATETIME_ACTION_INGEST]
        ajson_ingestor.ingest(self.without_history)
        ael = models.ArticleEvent.objects.all()
        self.assertEqual(ael.count(), len(expected_events))

    def test_ingest_creates_events(self):
        expected_events = [
            models.DATE_PREPRINT_PUBLISHED,
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

    def test_ingest_publish_creates_events(self):
        expected_events = [
            models.DATE_PREPRINT_PUBLISHED,
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

    def test_ingest_preprint_events(self):
        "preprint events whose dates vary don't accumulate"
        ajson_ingestor.ingest(self.with_history)
        preprint = models.ArticleEvent.objects.get(event="date-preprint")
        expected = datetime(2016, 4, 21, 0, 0, tzinfo=pytz.UTC)
        self.assertEqual(preprint.datetime_event, expected)

        new_date = "2016-04-22T00:00:00Z"  # one day in the future
        new_expected = datetime(2016, 4, 22, 0, 0, tzinfo=pytz.UTC)
        self.with_history["article"]["-history"]["preprint"]["date"] = new_date
        ajson_ingestor.ingest(self.with_history)
        preprint = models.ArticleEvent.objects.get(event="date-preprint")
        self.assertEqual(preprint.datetime_event, new_expected)

    def test_ingest_events_singletons(self):
        "certain events there should only be one of."
        ajson_ingestor.ingest(self.with_history)
        preprint = models.ArticleEvent.objects.get(event="date-preprint")
        expected = "https://www.biorxiv.org/content/10.1101/2019.08.22.6666666v1"
        self.assertEqual(preprint.uri, expected)

        new_uri = "http://example.org"
        self.with_history["article"]["-history"]["preprint"]["uri"] = new_uri
        ajson_ingestor.ingest(self.with_history)
        # only one, not many
        preprint = models.ArticleEvent.objects.get(event="date-preprint")
        self.assertEqual(preprint.uri, new_uri)

    def test_ingest_events_poa_doesnt_wipe_vor_events(self):
        ""


class RelatedEvents(base.TransactionBaseCase):
    def setUp(self):
        self.f1 = join(self.fixture_dir, "ajson", "elife-10627-v1.xml.json")
        self.ajson1 = self.load_ajson(self.f1, strip_relations=False)

        self.f2 = join(self.fixture_dir, "ajson", "elife-09560-v1.xml.json")
        self.ajson2 = self.load_ajson(self.f2, strip_relations=False)

    @patch("publisher.ajson_ingestor.aws_events.notify")
    def test_related_events(self, notify_mock):
        "aws_events.notify is called once for the article being ingested and once each for related articles"

        ajson_ingestor.ingest(self.ajson1)  # has 2 related

        def event_msid(index):
            args, first_arg = 1, 0
            return notify_mock.mock_calls[index][args][first_arg]

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

        ajson_ingestor.ingest(self.ajson1)  # has 2 related, 9561 and 9560

        with patch("publisher.ajson_ingestor.aws_events.notify") as notify_mock:

            def event_msid(index):
                args, first_arg = 1, 0
                return notify_mock.mock_calls[index][args][first_arg]

            ajson_ingestor.ingest(self.ajson2)  # has 2 related, 10627, 9561

            self.assertEqual(len(notify_mock.mock_calls), 3)

            # ensure the events have the right manuscript id
            self.assertEqual(event_msid(0), 9560)
            # internal relationships, lowest to highest msid
            self.assertEqual(event_msid(1), 9561)  # linked by 9560
            self.assertEqual(event_msid(2), 10627)  # links to 9560
