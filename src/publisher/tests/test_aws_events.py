import json
from unittest.mock import patch, Mock
from publisher import ajson_ingestor, aws_events
from . import base
from os.path import join
from django.urls import reverse
# from django.contrib.auth.models import User # don't do this
from django.contrib.auth import get_user_model  # do this
from django.test import Client, override_settings


def formsubgen(art):
    # tweaked from an actual POST that was captured
    avl = list(art.articleversion_set.all())
    artf = {
        "journal": art.journal.id,
        "manuscript_id": art.manuscript_id,
        "doi": art.doi,
        "date_received": art.date_received,
        "date_accepted": art.date_accepted,
        "date_initial_qc": "",
        "date_initial_decision": "",
        "initial_decision": "EF",
        "date_full_qc": "",
        "date_full_decision": "",
        "decision": "RVF",
        "date_rev1_qc": "",
        "date_rev1_decision": "",
        "rev1_decision": "AF",
        "date_rev2_qc": "",
        "date_rev2_decision": "",
        "rev2_decision": "",
        "date_rev3_qc": "",
        "date_rev3_decision": "",
        "rev3_decision": "",
        "date_rev4_qc": "",
        "date_rev4_decision": "",
        "rev4_decision": "",
        "volume": 4,
        "type": "research-article",
        "ejp_type": "RA",
        "articleversion_set-TOTAL_FORMS": len(avl),
        "articleversion_set-INITIAL_FORMS": len(avl),
        "articleversion_set-MIN_NUM_FORMS": 0,
        "articleversion_set-MAX_NUM_FORMS": 0,
        # ?
        # new av stub?
        "articleversion_set-__prefix__-id": "",
        "articleversion_set-__prefix__-article": art.id,
        "articleversion_set-__prefix__-datetime_published_0": "",
        "articleversion_set-__prefix__-datetime_published_1": "",
    }
    for i, av in enumerate(avl):
        artf.update(
            {
                "articleversion_set-%s-id" % i: av.id,
                "articleversion_set-%s-article" % i: av.article.id,
                "articleversion_set-%s-datetime_published_0"
                % i: av.datetime_published.strftime("%Y-%m-%d"),
                "articleversion_set-%s-datetime_published_1" % i: "00:00:00",
            }
        )
    return artf


class One(base.BaseCase):
    def setUp(self):
        self.ac = Client()

        user = get_user_model().objects.create_superuser(
            "john", "john@example.org", "password"
        )
        # https://docs.djangoproject.com/en/1.11/topics/testing/tools/#django.test.Client.force_login
        self.ac.force_login(user)

        ingest_these = [
            "elife-16695-v1.xml.json",
            # "elife-16695-v2.xml.json",
            # "elife-16695-v3.xml.json",
        ]
        ajson_dir = join(self.fixture_dir, "ajson")
        self.avs = []
        for ingestable in ingest_these:
            data = self.load_ajson(join(ajson_dir, ingestable))
            self.avs.append(ajson_ingestor.ingest_publish(data))

        self.msid = 16695
        self.art = self.avs[-1].article

    def tearDown(self):
        pass

    @override_settings(DEBUG=False)  # get past the early return in aws_events
    def test_admin_article_save_sends_event(self):
        "an event is sent when an article is updated from the article admin page"

        # we just need a successful form submission to test if an event is sent
        payload = formsubgen(self.art)

        # https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#admin-reverse-urls
        url = reverse("admin:publisher_article_change", args=(self.art.id,))

        expected_event = json.dumps({"type": "article", "id": self.msid})
        mock = Mock()
        with patch("publisher.aws_events.event_bus_conn", return_value=mock):
            resp = self.ac.post(url, payload, follow=False)
            self.assertEqual(
                resp.status_code, 302
            )  # temp redirect after successful submission
            mock.publish.assert_called_once_with(Message=expected_event)

    @override_settings(DEBUG=False)
    def test_admin_article_delete_sends_event(self):
        "an event is sent when an article is deleted from the article admin page"
        url = reverse("admin:publisher_article_delete", args=(self.art.id,))
        mock = Mock()
        expected_event = json.dumps({"type": "article", "id": self.msid})
        with patch("publisher.aws_events.event_bus_conn", return_value=mock):
            payload = {"post": "yes"}  # skips confirmation
            resp = self.ac.post(url, payload, follow=False)
            self.assertEqual(
                resp.status_code, 302
            )  # temp redirect after successful submission
            mock.publish.assert_called_once_with(Message=expected_event)

    @override_settings(DEBUG=False)
    def test_admin_articleversion_delete_sends_event(self):
        "an event is sent when an articleversion is deleted from the article admin page"

        # deleting an articleversion means selecting the 'delete' checkbox and clicking save
        payload = formsubgen(self.art)
        payload["articleversion_set-0-DELETE"] = "on"  # 'click' the delete checkbox

        url = reverse("admin:publisher_article_change", args=(self.art.id,))
        mock = Mock()
        expected_event = json.dumps({"type": "article", "id": self.msid})
        with patch("publisher.aws_events.event_bus_conn", return_value=mock):
            resp = self.ac.post(url, payload, follow=False)
            self.assertEqual(
                resp.status_code, 302
            )  # temp redirect after successful submission
            mock.publish.assert_called_once_with(Message=expected_event)


class Two(base.TransactionBaseCase):
    def setUp(self):
        self.f1 = join(self.fixture_dir, "ajson", "elife-10627-v1.xml.json")
        self.ajson1 = self.load_ajson(self.f1, strip_relations=False)

        self.f2 = join(self.fixture_dir, "ajson", "elife-09560-v1.xml.json")
        self.ajson2 = self.load_ajson(self.f2, strip_relations=False)

    def tearDown(self):
        pass

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


class DeferredEvents(base.BaseCase):
    def setUp(self):
        self.safeword = aws_events.SAFEWORD
        self.msid = 123

        @aws_events.defer
        def func(arg):
            return arg

        self.func = func

    def test_defer(self):
        cases = [
            ("a", "a"),
            ("b", "b"),
            ("c", "c"),
            (self.safeword, None),
            ("a", None),
            ("b", None),
            ("c", None),
            (self.safeword, ["a", "b", "c"]),
            ("a", "a"),
            ("b", "b"),
            ("c", "c"),
        ]

        for arg, expected in cases:
            self.assertEqual(expected, self.func(arg))

    def test_defer_nothing(self):
        cases = [(self.safeword, None), (self.safeword, None)]
        for arg, expected in cases:
            self.assertEqual(expected, self.func(arg))

    @override_settings(DEBUG=False)
    def test_notify_not_deferred(self):
        cases = [1, 2, 3]
        mock = Mock()
        for msid in cases:
            with patch("publisher.aws_events.event_bus_conn", return_value=mock):
                expected = json.dumps({"type": "article", "id": msid})
                self.assertEqual(expected, aws_events.notify(msid))

    @override_settings(DEBUG=False)
    def test_notify_deferred(self):
        "a notification is deferred"
        expected_event = json.dumps({"type": "article", "id": self.msid})
        cases = [
            (self.safeword, None),
            # three versions of the same article?
            (self.msid, None),
            (self.msid, None),
            (self.msid, None),
            (self.safeword, [expected_event]),
        ]
        mock = Mock()
        with patch("publisher.aws_events.event_bus_conn", return_value=mock):
            for msid, expected in cases:
                self.assertEqual(expected, aws_events.notify(msid))
            mock.publish.assert_called_once_with(Message=expected_event)
