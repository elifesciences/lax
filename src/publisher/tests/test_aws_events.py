import json
from unittest.mock import patch, Mock
from publisher import ajson_ingestor, aws_events
from .base import BaseCase
from os.path import join
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
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
        "articleversion_set-__prefix__-datetime_published_1": ""
    }
    for i, av in enumerate(avl):
        artf.update({
            "articleversion_set-%s-id" % i: av.id,
            "articleversion_set-%s-article" % i: av.article.id,
            "articleversion_set-%s-datetime_published_0" % i: av.datetime_published.strftime("%Y-%m-%d"),
            "articleversion_set-%s-datetime_published_1" % i: "00:00:00",
        })
    return artf

class One(BaseCase):
    def setUp(self):
        self.ac = Client()

        user = User.objects.create_superuser('john', 'john@example.org', 'password')
        # https://docs.djangoproject.com/en/1.11/topics/testing/tools/#django.test.Client.force_login
        self.ac.force_login(user)

        ingest_these = [
            "elife-16695-v1.xml.json",
            #"elife-16695-v2.xml.json",
            #"elife-16695-v3.xml.json",
        ]
        ajson_dir = join(self.fixture_dir, 'ajson')
        self.avs = []
        for ingestable in ingest_these:
            data = self.load_ajson(join(ajson_dir, ingestable))
            self.avs.append(ajson_ingestor.ingest_publish(data))

        self.msid = 16695
        self.art = self.avs[-1].article

    def tearDown(self):
        pass

    @override_settings(DEBUG=False) # get past the early return in aws_events
    def test_admin_article_save_sends_event(self):
        "an event is sent when an article is updated from the article admin page"

        # we just need a successful form submission to test if an event is sent
        payload = formsubgen(self.art)

        # https://docs.djangoproject.com/en/1.10/ref/contrib/admin/#admin-reverse-urls
        url = reverse("admin:publisher_article_change", args=(self.art.id,))

        expected_event = json.dumps({"type": "article", "id": self.msid})
        mock = Mock()
        with patch('publisher.aws_events.event_bus_conn', return_value=mock):
            resp = self.ac.post(url, payload, follow=False)
            self.assertEqual(resp.status_code, 302) # temp redirect after successful submission
            mock.publish.assert_called_once_with(Message=expected_event)

    @override_settings(DEBUG=False)
    def test_admin_article_delete_sends_event(self):
        "an event is sent when an article is deleted from the article admin page"
        url = reverse("admin:publisher_article_delete", args=(self.art.id,))
        mock = Mock()
        expected_event = json.dumps({"type": "article", "id": self.msid})
        with patch('publisher.aws_events.event_bus_conn', return_value=mock):
            payload = {'post': 'yes'} # skips confirmation
            resp = self.ac.post(url, payload, follow=False)
            self.assertEqual(resp.status_code, 302) # temp redirect after successful submission
            mock.publish.assert_called_once_with(Message=expected_event)

    @override_settings(DEBUG=False)
    def test_admin_articleversion_delete_sends_event(self):
        "an event is sent when an articleversion is deleted from the article admin page"

        # deleting an articleversion means selecting the 'delete' checkbox and clicking save
        payload = formsubgen(self.art)
        payload["articleversion_set-0-DELETE"] = "on" # 'click' the delete checkbox

        url = reverse("admin:publisher_article_change", args=(self.art.id,))
        mock = Mock()
        expected_event = json.dumps({"type": "article", "id": self.msid})
        with patch('publisher.aws_events.event_bus_conn', return_value=mock):
            resp = self.ac.post(url, payload, follow=False)
            self.assertEqual(resp.status_code, 302) # temp redirect after successful submission
            mock.publish.assert_called_once_with(Message=expected_event)

class Foo(BaseCase):
    def test_defer(self):
        safeword = 'testme'

        cases = [
            ('a', 'a'),
            ('b', 'b'),
            ('c', 'c'),

            (safeword, None),

            ('a', None),
            ('b', None),
            ('c', None),

            (safeword, ['a', 'b', 'c']),

            ('a', 'a'),
            ('b', 'b'),
            ('c', 'c'),

        ]

        @aws_events.defer(safeword)
        def func(arg):
            return arg

        for arg, expected in cases:
            self.assertEqual(expected, func(arg))

    '''
    def test_defer_complex(self):
        safeword = 'testme'

        cases = [
            (('foo', {'bar': 'baz'}), ('foo', {'bar': 'baz'})),
            (('baz', {'bar': 'foo'}), ('baz', {'bar': 'foo'})),

            (safeword, None),

            (('foo', {'bar': 'baz'}), None),
            ('a', None),
            (('baz', {'bar': 'foo'}), None),

            (safeword, [
                ('foo', {'bar': 'baz'}),
                'a',
                ('baz', {'bar': 'foo'}),
            ]),

            ('b', 'b'),
            (('baz', {'bar': 'foo'}), ('baz', {'bar': 'foo'})),
        ]

        @aws_events.defer(safeword)
        def func(arg):
            return arg

        for arg, expected in cases:
            self.assertEqual(expected, func(arg))
    '''
