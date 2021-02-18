from os.path import join
import json
from . import base
from unittest.mock import patch
from publisher import fragment_logic as logic, ajson_ingestor, models
from publisher.utils import StateError
from datetime import datetime
from django.test import override_settings
import pytest
from jsonschema import ValidationError

"""
ingesting an article creates our initial ArticleFragment, the 'xml->json' fragment
at position 0.

all other fragments are merged into this initial fragment

the result is valid article json

"""


class ArticleIngestFragmentLogic(base.BaseCase):
    def setUp(self):
        self.ajson_fixture = join(self.fixture_dir, "ajson", "elife-01968-v1.xml.json")
        self.ajson = json.load(open(self.ajson_fixture, "r"))
        self.msid = self.ajson["article"]["id"]
        self.version = self.ajson["article"]["version"]  # v1

    def test_ajson_ingest_creates_article_fragment(self):
        self.assertEqual(models.ArticleFragment.objects.count(), 0)
        ajson_ingestor.ingest(self.ajson)
        self.assertEqual(models.ArticleFragment.objects.count(), 1)


class FragmentLogic(base.BaseCase):
    def setUp(self):
        self.ajson_fixture = join(self.fixture_dir, "ajson", "elife-01968-v1.xml.json")
        self.ajson = json.load(open(self.ajson_fixture, "r"))
        self.msid = self.ajson["article"]["id"]
        self.version = self.ajson["article"]["version"]  # v1

        # populate with an article. CREATES A FRAGMENT
        self.av = ajson_ingestor.ingest_publish(self.ajson)

    def tearDown(self):
        pass

    def test_add_fragment(self):
        "a fragment of article data can be recorded against an Article"
        # `setUp` creates a fragment by ingesting article
        self.assertEqual(models.ArticleFragment.objects.count(), 1)

        fragment = {"title": "pants. party"}
        fragobj, created, updated = logic.add(self.msid, "foo", fragment)
        self.assertEqual(models.ArticleFragment.objects.count(), 2)
        self.assertEqual(fragment, fragobj.fragment)

    def test_update_fragment(self):
        "a fragment of article data can be updated by adding it again with different content"

        # ensure we have something that resembles the ingest data
        self.assertEqual(models.ArticleFragment.objects.count(), 1)
        frag = logic.get(self.av, "xml->json").fragment
        self.assertTrue("title" in frag)

        # now update it with some garbage
        data = {"title": "pants-party"}
        logic.add(self.av, "xml->json", data, pos=0, update=True)

        # ensure we've just destroyed our very important data
        frag = logic.get(self.av, "xml->json").fragment
        self.assertEqual(frag, data)

    def test_delete_fragment(self):
        self.assertEqual(models.ArticleFragment.objects.count(), 1)
        fragment = {"title": "pants. party"}
        logic.add(self.msid, "foo", fragment)
        self.assertEqual(models.ArticleFragment.objects.count(), 2)
        logic.rm(self.msid, "foo")
        self.assertEqual(models.ArticleFragment.objects.count(), 1)


class FragmentMerge(base.BaseCase):
    def setUp(self):
        # poa, published 2016-08-16T00:00:00Z
        self.ajson_fixture = join(self.fixture_dir, "ajson", "elife-16695-v1.xml.json")
        self.ajson = json.load(open(self.ajson_fixture, "r"))
        self.msid = self.ajson["article"]["id"]
        self.version = self.ajson["article"]["version"]  # v1
        self.av = ajson_ingestor.ingest_publish(self.ajson)

    def test_merge_fragments(self):
        logic.add(self.av, "xml->json", {"title": "foo"}, update=True)
        logic.add(self.msid, "frag1", {"body": "bar"})
        logic.add(self.msid, "frag2", {"foot": "baz"})

        expected = {"title": "foo", "body": "bar", "foot": "baz"}
        self.assertEqual(expected, logic.merge(self.av))

    def test_merge_overwrite_fragments(self):
        logic.add(
            self.av, "xml->json", {"title": "foo"}, update=True
        )  # destroys original article json
        logic.add(self.msid, "frag1", {"title": "bar"})
        logic.add(self.msid, "frag2", {"title": "baz"})

        expected = {"title": "baz"}
        self.assertEqual(expected, logic.merge(self.av))

    def test_fragment_ordering(self):
        logic.add(self.av, "xml->json", {"title": "foo"}, update=True)
        logic.add(self.msid, "frag1", {"body": "bar"})
        logic.add(self.msid, "frag2", {"foot": "baz"})

        # order of insertion is preserved
        expected_order = ["xml->json", "frag1", "frag2"]
        for given, expected in zip(
            models.ArticleFragment.objects.all(), expected_order
        ):
            self.assertEqual(given.type, expected)

    def test_fragment_ordering_explicit(self):
        logic.add(self.av, "xml->json", {"title": "foo"}, update=True)  # implicit pos=1
        logic.add(self.msid, "frag1", {"title": "bar"}, pos=2)  # explicit pos=2
        logic.add(self.msid, "frag2", {"title": "baz"}, pos=1)  # explicit pos=1

        # order of insertion is preserved + explicit ordering
        expected_order = ["xml->json", "frag2", "frag1"]
        for given, expected in zip(
            models.ArticleFragment.objects.all(), expected_order
        ):
            self.assertEqual(given.type, expected)

        expected = {"title": "bar"}
        self.assertEqual(expected, logic.merge(self.av))

    def test_valid_merge_updates_article_version_fields(self):
        "when a fragment is added, if the merge results in valid article-json, the results of the merge are stored"
        # add fragment
        placeholders = {"title": "bar"}
        logic.add(self.msid, "foo", placeholders)

        # merge fragments
        self.assertTrue(logic.set_article_json(self.av, quiet=False))

        # re-fetch av
        av = self.freshen(self.av)
        self.assertTrue(av.article_json_v1)
        self.assertTrue(av.article_json_v1_snippet)
        self.assertTrue(av.article_json_hash)

    def test_merge_sets_status_date_correctly_poa_v1(self):
        "statusDate for a v1 poa is correctly set: earliest POA if POA, earliest VOR if VOR"
        # poa, published 2016-08-16T00:00:00Z
        av = self.freshen(self.av)
        expected = "2016-08-16T00:00:00Z"
        self.assertEqual(expected, av.article_json_v1["statusDate"])

    def test_merge_sets_status_date_correctly_poa_v2(self):
        "statusDate for a v2 poa is correctly set: earliest POA if POA, earliest VOR if VOR"
        av = self.freshen(self.av)
        expected = "2016-08-16T00:00:00Z"
        self.assertEqual(expected, av.article_json_v1["statusDate"])

        # load v2 as a poa
        fixture = join(self.fixture_dir, "ajson", "elife-16695-v2.xml.json")
        data = json.load(open(fixture, "r"))
        data["status"] = models.POA
        data["published"] = "2016-08-17T00:00:00Z"  # v2 POA published a day later
        av2 = ajson_ingestor.ingest_publish(data)

        # nothing should have changed
        av2 = self.freshen(av)
        self.assertEqual(expected, av2.article_json_v1["statusDate"])

    def test_merge_sets_status_date_correctly_vor_v2(self):
        "statusDate for a v2 vor is correctly set: earliest POA if POA, earliest VOR if VOR"
        # load v2 vor
        fixture = join(self.fixture_dir, "ajson", "elife-16695-v2.xml.json")
        data = json.load(open(fixture, "r"))
        av2 = ajson_ingestor.ingest_publish(data)
        av2.datetime_published = datetime(
            year=2016, month=8, day=17
        )  # v2 VOR published a day later
        av2.save()
        logic.set_article_json(av2, quiet=False)

        av1 = self.freshen(self.av)
        expected = "2016-08-16T00:00:00Z"
        self.assertEqual(expected, av1.article_json_v1["statusDate"])

        av2 = self.freshen(av2)
        expected = "2016-08-17T00:00:00Z"
        self.assertEqual(expected, av2.article_json_v1["statusDate"])

    def test_merge_ignores_unpublished_vor_when_setting_status_date(self):
        "the first unpublished VOR doesn't get a value until it's published"
        fixture = join(self.fixture_dir, "ajson", "elife-16695-v2.xml.json")
        data = json.load(open(fixture, "r"))
        av2 = ajson_ingestor.ingest(data)  # ingested, not published

        av1 = self.freshen(self.av)
        expected = "2016-08-16T00:00:00Z"
        self.assertEqual(expected, av1.article_json_v1["statusDate"])

        av2 = self.freshen(av2)
        self.assertFalse(av2.datetime_published)  # v2 is not published yet
        self.assertTrue(av2.article_json_v1)  # has article json attached

        # v2 vor hasn't been published
        self.assertEqual("preview", av2.article_json_v1["stage"])
        self.assertFalse("statusDate" in av2.article_json_v1)
        self.assertFalse("versionDate" in av2.article_json_v1)

    def test_invalid_merge_preserves_article_json(self):
        """the previously set article-json and it's snippet are preserved if the 
        current set of fragments no longer validate when merged (for any reason)"""

        expected = "A Cryptochrome 2 Mutation Yields Advanced Sleep Phase in Human"
        original_title = self.av.article_json_v1["title"]
        self.assertEqual(expected, original_title)

        # simulates a fragment that was once valid but no longer is.
        # perhaps an empty title was once valid but now has a minimum length..
        fragment = models.ArticleFragment(
            article=self.av.article,
            version=self.av.version,
            type="bad-frag",
            fragment={"title": ""},
            position=1,
        )
        fragment.save()

        # ensure current set of fragments is now invalid.
        result = logic.merge(self.av)
        result = logic.pre_process(self.av, result)
        self.assertFalse(logic.valid(result))

        self.freshen(self.av)

        # article is still serving up invalid content :(
        self.assertTrue(self.av.article_json_v1)

        # attempting to re-set the article-json will fail (invalid),
        # even when `quiet` is `True`.
        self.assertRaises(StateError, logic.set_article_json, self.av, quiet=True)

        # article-json with the original title is still being served up
        self.freshen(self.av)
        self.assertEqual(expected, self.av.article_json_v1["title"])

    def test_merged_datetime_content(self):
        "microseconds are stripped from the datetime published value when stored"
        # modify article data
        pubdate = datetime(
            year=2001, month=1, day=1, hour=1, minute=1, second=1, microsecond=666
        )
        self.av.datetime_published = pubdate
        self.av.save()

        # merge, re-validate, re-set
        logic.set_article_json(self.av, quiet=False)

        av = self.freshen(self.av)
        expected_version_date = "2001-01-01T01:01:01Z"  # no microsecond component
        self.assertEqual(expected_version_date, av.article_json_v1["versionDate"])

    @override_settings(MERGE_FOREIGN_FRAGMENTS=False)
    def test_foreign_snippets_can_be_excluded(self):
        "foreign fragments can be added but fail to merge if disallowed"
        logic.add(self.av, "xml->json", {"title": "foo"}, update=True)
        logic.add(self.msid, "frag1", {"body": "bar"})
        logic.add(self.msid, "frag2", {"foot": "baz"})
        self.assertEqual(3, models.ArticleFragment.objects.count())

        expected = {"title": "foo"}
        self.assertEqual(expected, logic.merge(self.av))

    def test_reset_merged_fragments(self):
        "article-json can be reset, ignoring any foreign (unknown) fragment types."
        logic.add(self.msid, "frag1", {"title": "foo"})
        logic.add(self.msid, "frag2", {"body": "bar"})
        logic.add(self.msid, "frag3", {"foot": "baz"})

        result = logic.merge(self.av)
        self.assertEqual("foo", result["title"])
        self.assertEqual("bar", result["body"])
        self.assertEqual("baz", result["foot"])

        # just to ensure we're dealing with a whole article fixture
        self.assertEqual("published", result["stage"])

        with patch("publisher.fragment_logic.settings.MERGE_FOREIGN_FRAGMENTS", False):
            logic.reset_merged_fragments(self.av.article)
            result = logic.merge(self.av)
            self.assertEqual(
                "A Cryptochrome 2 Mutation Yields Advanced Sleep Phase in Human",
                result["title"],
            )
            self.assertFalse("bar" in result)
            self.assertFalse("baz" in result)
            self.assertEqual("published", result["stage"])


"""
an article snippet is a subset of article data defined by the api-raml.

it is created at ingestion and stored alongside the complete article-json.

it is used in article listing responses.
"""


def test_extract_snippet():
    ajson_fixture = join(base.FIXTURE_DIR, "ajson", "elife-01968-v1.xml.json")
    ajson_snippet_fixture = join(
        base.FIXTURE_DIR, "ajson", "elife-01968-v1.snippet.xml.json"
    )
    merged_ajson = json.load(open(ajson_fixture, "r"))
    expected = json.load(open(ajson_snippet_fixture, "r"))

    # the article-json at this point has just finished pre-processing, all of the hidden fields
    # have been stripped, extra fields added, etc and it's about to be inserted into the db.
    # the fixture we use comes from bot-lax and contains a snippet and journal information that
    # lax discards early on.
    merged_ajson = merged_ajson["article"]
    assert expected == logic.extract_snippet(merged_ajson)


def test_extract_snippet_empty_cases():
    case_list = [None, {}, [], ""]
    expected = None
    for case in case_list:
        assert expected == logic.extract_snippet(case)


def test_valid_snippet():
    "snippets can be validated."
    ajson_fixture = join(base.FIXTURE_DIR, "ajson", "elife-01968-v1.xml.json")
    merged_ajson = json.load(open(ajson_fixture, "r"))
    snippet = logic.extract_snippet(merged_ajson["article"])
    assert snippet == logic.valid_snippet(snippet, quiet=False)


def test_invalid_snippet():
    "snippets can be validated, invalid data raise a `ValidationError` or return None if `quiet=True`."
    ajson_fixture = join(base.FIXTURE_DIR, "ajson", "elife-01968-v1.xml.json")
    merged_ajson = json.load(open(ajson_fixture, "r"))
    snippet = logic.extract_snippet(merged_ajson["article"])
    snippet["status"] = "pants"
    assert not logic.valid_snippet(snippet, quiet=True)
    with pytest.raises(ValidationError):
        logic.valid_snippet(snippet, quiet=False)
