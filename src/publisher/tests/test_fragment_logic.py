import glob
from os.path import join
import json
from .base import BaseCase
from publisher import logic as article_logic, fragment_logic as logic, ajson_ingestor, models
from datetime import datetime

"""
ingesting an article creates our initial ArticleFragment, the 'xml->json' fragment
at position 0.

all other fragments are merged into this initial fragment

the result is valid article json

"""

class ArticleIngestFragmentLogic(BaseCase):
    def setUp(self):
        self.ajson_fixture = join(self.fixture_dir, 'ajson', 'elife-01968-v1.xml.json')
        self.ajson = json.load(open(self.ajson_fixture, 'r'))
        self.msid = self.ajson['article']['id']
        self.version = self.ajson['article']['version'] # v1

    def test_ajson_ingest_creates_article_fragment(self):
        self.assertEqual(models.ArticleFragment.objects.count(), 0)
        ajson_ingestor.ingest(self.ajson)
        self.assertEqual(models.ArticleFragment.objects.count(), 1)


class FragmentLogic(BaseCase):
    def setUp(self):
        self.ajson_fixture = join(self.fixture_dir, 'ajson', 'elife-01968-v1.xml.json')
        self.ajson = json.load(open(self.ajson_fixture, 'r'))
        self.msid = self.ajson['article']['id']
        self.version = self.ajson['article']['version'] # v1

        # populate with an article. CREATES A FRAGMENT
        self.av = ajson_ingestor.ingest_publish(self.ajson)

    def tearDown(self):
        pass

    def test_add_fragment(self):
        "a fragment of article data can be recorded against an Article"
        # `setUp` creates a fragment by ingesting article
        self.assertEqual(models.ArticleFragment.objects.count(), 1)

        fragment = {'title': 'pants. party'}
        fragobj, created, updated = logic.add(self.msid, 'foo', fragment)
        self.assertEqual(models.ArticleFragment.objects.count(), 2)
        self.assertEqual(fragment, fragobj.fragment)

    def test_update_fragment(self):
        "a fragment of article data can be updated by adding it again with different content"

        # ensure we have something that resembles the ingest data
        self.assertEqual(models.ArticleFragment.objects.count(), 1)
        frag = logic.get(self.av, 'xml->json').fragment
        self.assertTrue('title' in frag)

        # now update it with some garbage
        data = {'title': 'pants-party'}
        logic.add(self.av, 'xml->json', data, pos=0, update=True)

        # ensure we've just destroyed our very important data
        frag = logic.get(self.av, 'xml->json').fragment
        self.assertEqual(frag, data)

    def test_delete_fragment(self):
        self.assertEqual(models.ArticleFragment.objects.count(), 1)
        fragment = {'title': 'pants. party'}
        logic.add(self.msid, 'foo', fragment)
        self.assertEqual(models.ArticleFragment.objects.count(), 2)
        logic.rm(self.msid, 'foo')
        self.assertEqual(models.ArticleFragment.objects.count(), 1)

class FragmentMerge(BaseCase):
    def setUp(self):
        # poa, published 2016-08-16T00:00:00Z
        self.ajson_fixture = join(self.fixture_dir, 'ajson', 'elife-16695-v1.xml.json')
        self.ajson = json.load(open(self.ajson_fixture, 'r'))
        self.msid = self.ajson['article']['id']
        self.version = self.ajson['article']['version'] # v1
        self.av = ajson_ingestor.ingest_publish(self.ajson)

    def test_merge_fragments(self):
        logic.add(self.av, 'xml->json', {'title': 'foo'}, update=True)
        logic.add(self.msid, 'frag1', {'body': 'bar'})
        logic.add(self.msid, 'frag2', {'foot': 'baz'})

        expected = {'title': 'foo', 'body': 'bar', 'foot': 'baz'}
        self.assertEqual(expected, logic.merge(self.av))

    def test_merge_overwrite_fragments(self):
        logic.add(self.av, 'xml->json', {'title': 'foo'}, update=True) # destroys original article json
        logic.add(self.msid, 'frag1', {'title': 'bar'})
        logic.add(self.msid, 'frag2', {'title': 'baz'})

        expected = {'title': 'baz'}
        self.assertEqual(expected, logic.merge(self.av))

    def test_fragment_ordering(self):
        logic.add(self.av, 'xml->json', {'title': 'foo'}, update=True)
        logic.add(self.msid, 'frag1', {'body': 'bar'})
        logic.add(self.msid, 'frag2', {'foot': 'baz'})

        # order of insertion is preserved
        expected_order = ['xml->json', 'frag1', 'frag2']
        for given, expected in zip(models.ArticleFragment.objects.all(), expected_order):
            self.assertEqual(given.type, expected)

    def test_fragment_ordering_explicit(self):
        logic.add(self.av, 'xml->json', {'title': 'foo'}, update=True) # implicit pos=1
        logic.add(self.msid, 'frag1', {'title': 'bar'}, pos=2) # explicit pos=2
        logic.add(self.msid, 'frag2', {'title': 'baz'}, pos=1) # explicit pos=1

        # order of insertion is preserved + explicit ordering
        expected_order = ['xml->json', 'frag2', 'frag1']
        for given, expected in zip(models.ArticleFragment.objects.all(), expected_order):
            self.assertEqual(given.type, expected)

        expected = {'title': 'bar'}
        self.assertEqual(expected, logic.merge(self.av))

    def test_valid_merge_updates_article_version_fields(self):
        "when a fragment is added, if the merge results in valid article-json, the results of the merge are stored"
        # add fragment
        placeholders = {'title': 'bar'}
        logic.add(self.msid, 'foo', placeholders)

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
        expected = '2016-08-16T00:00:00Z'
        self.assertEqual(expected, av.article_json_v1['statusDate'])

    def test_merge_sets_status_date_correctly_poa_v2(self):
        "statusDate for a v2 poa is correctly set: earliest POA if POA, earliest VOR if VOR"
        av = self.freshen(self.av)
        expected = '2016-08-16T00:00:00Z'
        self.assertEqual(expected, av.article_json_v1['statusDate'])

        # load v2 as a poa
        fixture = join(self.fixture_dir, 'ajson', 'elife-16695-v2.xml.json')
        data = json.load(open(fixture, 'r'))
        data['status'] = models.POA
        data['published'] = '2016-08-17T00:00:00Z' # v2 POA published a day later
        av2 = ajson_ingestor.ingest_publish(data)

        # nothing should have changed
        av2 = self.freshen(av)
        self.assertEqual(expected, av2.article_json_v1['statusDate'])

    def test_merge_sets_status_date_correctly_vor_v2(self):
        "statusDate for a v2 vor is correctly set: earliest POA if POA, earliest VOR if VOR"
        # load v2 vor
        fixture = join(self.fixture_dir, 'ajson', 'elife-16695-v2.xml.json')
        data = json.load(open(fixture, 'r'))
        av2 = ajson_ingestor.ingest_publish(data)
        av2.datetime_published = datetime(year=2016, month=8, day=17) # v2 VOR published a day later
        av2.save()
        logic.set_article_json(av2, quiet=False)

        av1 = self.freshen(self.av)
        expected = '2016-08-16T00:00:00Z'
        self.assertEqual(expected, av1.article_json_v1['statusDate'])

        av2 = self.freshen(av2)
        expected = '2016-08-17T00:00:00Z'
        self.assertEqual(expected, av2.article_json_v1['statusDate'])

    def test_merge_ignores_unpublished_vor_when_setting_status_date(self):
        "the first unpublished VOR doesn't get a value until it's published"
        fixture = join(self.fixture_dir, 'ajson', 'elife-16695-v2.xml.json')
        data = json.load(open(fixture, 'r'))
        av2 = ajson_ingestor.ingest(data) # ingested, not published

        av1 = self.freshen(self.av)
        expected = '2016-08-16T00:00:00Z'
        self.assertEqual(expected, av1.article_json_v1['statusDate'])

        av2 = self.freshen(av2)
        self.assertFalse(av2.datetime_published) # v2 is not published yet
        self.assertTrue(av2.article_json_v1) # has article json attached

        # v2 vor hasn't been published
        self.assertEqual('preview', av2.article_json_v1['stage'])
        self.assertFalse('statusDate' in av2.article_json_v1)
        self.assertFalse('versionDate' in av2.article_json_v1)

    def test_invalid_merge_deletes_article_json(self):
        fragment = models.ArticleFragment.objects.all()[0]
        # simulate a value that was once valid but no longer is
        fragment.fragment['title'] = ''
        fragment.save()

        # ensure fragment is now invalid.
        self.assertFalse(logic.merge_if_valid(self.av))

        # article is still serving up invalid content :(
        self.assertTrue(self.av.article_json_v1)

        # ensure delete happens successfully
        self.assertFalse(logic.set_article_json(self.av, quiet=True))

        # article is no longer serving up invalid content :)
        av = self.freshen(self.av)
        self.assertFalse(av.article_json_v1)

    def test_merged_datetime_content(self):
        "microseconds are stripped from the datetime published value when stored"
        # modify article data
        pubdate = datetime(year=2001, month=1, day=1, hour=1, minute=1, second=1, microsecond=666)
        self.av.datetime_published = pubdate
        self.av.save()

        # merge, re-validate, re-set
        logic.set_article_json(self.av, quiet=False)

        av = self.freshen(self.av)
        expected_version_date = '2001-01-01T01:01:01Z' # no microsecond component
        self.assertEqual(expected_version_date, av.article_json_v1['versionDate'])


class CLI(BaseCase):
    def setUp(self):
        self.nom = 'revalidate'

        # publish four valid articles, ensure each is in different states

        fixture_list = [
            '01968', # SET
            '16695', # RESET
            '20105', # UNSET
            '20125', # NOTSET
        ]
        self.msid1, self.msid2, self.msid3, self.msid4 = fixture_list
        self.version = '1'

        for msid in fixture_list:
            fixture_path = join(self.fixture_dir, 'ajson', 'elife-%s-v1.xml.json' % msid)
            ajson_ingestor.ingest_publish(json.load(open(fixture_path, 'r')))

        # SET
        # remove the valid ajson so it gets set
        av = article_logic.article_version(self.msid1, self.version)
        av.article_json_v1 = av.article_json_v1_snippet = None
        av.save()

        # RESET
        # already valid, nothing to do

        # UNSET
        # ensure the fragment is now invalid
        av = article_logic.article_version(self.msid3, self.version)
        frag = logic.get(av, models.XML2JSON)
        frag.fragment['title'] = ''
        frag.save()

        # NOTSET
        # remove the valid article-json
        # ensure fragment is invalid and won't be set
        av = article_logic.article_version(self.msid4, self.version)
        av.article_json_v1 = av.article_json_v1_snippet = None
        av.save()
        frag = logic.get(av, models.XML2JSON)
        frag.fragment['title'] = ''
        frag.save()

    def test_revalidate_article_version_from_cli(self):
        "the revalidate command can be called from the CLI for a specific article version"
        args = [self.nom, '--id', self.msid1, '--version', self.version]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

        report = json.loads(stdout)
        self.assertEqual(report['total-set'], 1)
        self.assertEqual(report['total-with-article-json'], 1)

    def test_revalidate_article_from_cli(self):
        "the revalidate command can be called from the CLI for all versions of an article"
        # we need to ingest some more versions here
        fixtures = sorted(glob.glob(join(self.fixture_dir, 'ajson', 'elife-%s-v*.xml.json' % self.msid2)))
        for fixture in fixtures[1:]: # don't reingest v1
            ajson_ingestor.ingest_publish(json.load(open(fixture, 'r')))
        args = [self.nom, '--id', self.msid2]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

        report = json.loads(stdout)
        self.assertEqual(report['total-reset'], 3) # msid2 is untouched, all are valid, all should be reset

    def test_revalidate_all_from_cli(self):
        args = [self.nom]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

        report = json.loads(stdout)
        self.assertEqual(report['total-set'], 1)
        self.assertEqual(report['total-unset'], 1)
        self.assertEqual(report['total-reset'], 1)
        self.assertEqual(report['total-not-set'], 1)

        # SET
        av = article_logic.article_version(self.msid1, self.version)
        self.assertTrue(av.article_json_v1)
        self.assertTrue(av.article_json_v1_snippet)

        # RESET
        av = article_logic.article_version(self.msid2, self.version)
        self.assertTrue(av.article_json_v1)
        self.assertTrue(av.article_json_v1_snippet)

        # UNSET
        av = article_logic.article_version(self.msid3, self.version)
        self.assertFalse(av.article_json_v1)
        self.assertFalse(av.article_json_v1_snippet)

        # NOTSET
        av = article_logic.article_version(self.msid4, self.version)
        self.assertFalse(av.article_json_v1)
        self.assertFalse(av.article_json_v1_snippet)

    def test_revalidate_from_cli_dry_run(self):
        "a dry run doesn't modify anything. the report should be the same as an actual run, but with no changes"
        args = [self.nom, '--dry-run']
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

        report = json.loads(stdout)
        self.assertEqual(report['total-set'], 1)
        self.assertEqual(report['total-unset'], 1)
        self.assertEqual(report['total-reset'], 1)
        self.assertEqual(report['total-not-set'], 1)

        # SET (nothing SET)
        av = article_logic.article_version(self.msid1, self.version)
        self.assertFalse(av.article_json_v1)
        self.assertFalse(av.article_json_v1_snippet)

        # RESET (still SET)
        av = article_logic.article_version(self.msid2, self.version)
        self.assertTrue(av.article_json_v1)
        self.assertTrue(av.article_json_v1_snippet)

        # UNSET (nothing UNSET)
        av = article_logic.article_version(self.msid3, self.version)
        self.assertTrue(av.article_json_v1)
        self.assertTrue(av.article_json_v1_snippet)

        # NOTSET (nothing ... not ... set ?)
        av = article_logic.article_version(self.msid4, self.version)
        self.assertFalse(av.article_json_v1)
        self.assertFalse(av.article_json_v1_snippet)
