from StringIO import StringIO
from os.path import join
import json
from datetime import datetime
from base import BaseCase
from publisher import ajson_ingestor, models, utils
from publisher.ajson_ingestor import StateError
#from unittest import skip
from django.core.management import call_command

class Ingest(BaseCase):
    def setUp(self):
        self.ajson_fixture1 = join(self.fixture_dir, 'ajson', 'elife.01968.json')
        self.ajson = json.load(open(self.ajson_fixture1, 'r'))

        self.ajson_fixture2 = join(self.fixture_dir, 'ajson', 'elife.01968-invalid.json')
        self.invalid_ajson = json.load(open(self.ajson_fixture2, 'r'))

    def tearDown(self):
        pass

    def test_article_ingest(self):
        """valid article-json is successfully ingested, creating an article,
        an article version and storing the ingestion request"""
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

        ajson_ingestor.ingest(self.ajson)

        self.assertEqual(models.Journal.objects.count(), 1)
        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)

    def test_article_ingest_does_not_publish(self):
        """ingesting article json does not cause an article to become published
        (gain a published date) even if a published date was supplied"""
        expected = "2016-04-13T01:00:00"
        self.ajson['article']['published'] = expected
        _, _, av = ajson_ingestor.ingest(self.ajson)
        self.assertNotEqual(av.datetime_published, expected)

    def test_article_ingest_update(self):
        "ingesting article data twice successfully updates the article"
        _, _, av = ajson_ingestor.ingest(self.ajson)

        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        self.assertEqual(av.title, self.ajson['article']['title'])
        self.assertEqual(av.datetime_published, None) # not published

        # do it again to cause an update
        expected_title = 'flub'
        self.ajson['article']['title'] = expected_title
        _, _, av = ajson_ingestor.ingest(self.ajson)

        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        self.assertEqual(av.title, expected_title)
        self.assertEqual(av.datetime_published, None) # still not published

    def test_article_update_does_not_publish(self):
        "ingesting article data twice still does not cause publication"
        _, _, av = ajson_ingestor.ingest(self.ajson)
        self.assertEqual(av.datetime_published, None)

        expected = "2016-04-13T01:00:00"
        self.ajson['article']['published'] = expected

        _, _, av = ajson_ingestor.ingest(self.ajson)
        self.assertEqual(av.datetime_published, None)

    def test_article_ingest_fails_for_published_articles(self):
        "ingesting article data for a published article version fails"
        _, _, av = ajson_ingestor.ingest(self.ajson)
        # edit data directly
        av.datetime_published = '2001-01-01'
        av.save()
        self.assertTrue(av.published())

        # attempt another ingest
        self.assertRaises(StateError, ajson_ingestor.ingest, self.ajson)

    def test_article_ingest_for_published_articles_succeeds_if_forced(self):
        "ingesting article data for a published article version succeeds if force=True"
        _, _, av = ajson_ingestor.ingest(self.ajson)
        # edit data directly
        av.datetime_published = '2001-01-01'
        av.save()
        self.assertTrue(av.published())

        # attempt another ingest
        expected_title = 'foo'
        self.ajson['article']['title'] = expected_title
        _, _, av = ajson_ingestor.ingest(self.ajson, force=True)
        self.assertEqual(av.title, expected_title)

    def test_article_ingest_bad_journal(self):
        "bad journal data will fail an ingest of article json"
        self.assertEqual(models.Journal.objects.count(), 0)
        del self.ajson['journal']
        self.assertRaises(Exception, ajson_ingestor.ingest, self.ajson)
        self.assertEqual(models.Journal.objects.count(), 0)

    def test_article_ingest_bad_article(self):
        "bad article data will fail an ingest of article json"
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        del self.ajson['article']
        self.assertRaises(Exception, ajson_ingestor.ingest, self.ajson)
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)

    def test_article_ingest_bad_article_version(self):
        "bad article version data will fail an ingest of article json"
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)
        del self.ajson['article']['title']
        self.assertRaises(Exception, ajson_ingestor.ingest, self.ajson)
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

    def test_out_of_sequence_ingest_fails(self):
        "attempting to ingest an article with a version greater than 1 when no article versions currently exists fails"
        # no article exists, attempt to ingest a v2
        self.assertEqual(models.ArticleVersion.objects.count(), 0)
        self.ajson['article']['version'] = 2
        self.assertRaises(StateError, ajson_ingestor.ingest, self.ajson)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

    def test_out_of_sequence_ingest_fails2(self):
        "attempting to ingest an article with a version greater than another unpublished version fails"
        _, _, av = ajson_ingestor.ingest(self.ajson) # v1
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        self.assertEqual(av.version, 1)

        # now attempt to ingest a v3
        self.ajson['article']['version'] = 3
        self.assertRaises(StateError, ajson_ingestor.ingest, self.ajson)

        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        av = self.freshen(av)
        self.assertEqual(av.version, 1) # assert the version hasn't changed

    def test_ingest_dry_run(self):
        "specifying a dry run does not commit changes to database"
        self.assertEqual(models.ArticleVersion.objects.count(), 0)
        _, _, av = ajson_ingestor.ingest(self.ajson, dry_run=True)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)
        self.assertEqual(av.version, 1) # all the data that would have been saved

    # json ingestion has yet to be dealt with properly

    # def test_article_json_stored_if_valid(self):
    #    "only valid article json is ever stored"
    #    self.assertRaises(StateError, ajson_ingestor.ingest, self.invalid_ajson)
    #    self.assertEqual(models.ArticleVersion.objects.count(), 0)

    # def test_article_json_not_stored_if_invalid(self):
    #    "invalid article json is not stored if it fails validation"
    #    assert False


class Publish(BaseCase):
    def setUp(self):
        self.ajson_fixture1 = join(self.fixture_dir, 'ajson', 'elife.01968.json')
        self.ajson = json.load(open(self.ajson_fixture1, 'r'))
        self.msid = self.ajson['article']['id']
        self.version = self.ajson['article']['version'] # v1

    def tearDown(self):
        pass

    def test_article_publish_v1(self):
        "an unpublished v1 article can be successfully published"
        _, _, av = ajson_ingestor.ingest(self.ajson)
        self.assertEqual(models.Journal.objects.count(), 1)
        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        self.assertFalse(av.published())

        # publish
        av = ajson_ingestor.publish(self.msid, self.version)

        # aaand just make sure we still have the expected number of objects
        self.assertEqual(models.Journal.objects.count(), 1)
        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)

        self.assertTrue(av.published())
        self.assertTrue(isinstance(av.datetime_published, datetime))

        # the pubdate of an unpublished v1 article is the same as that found in the
        # given json.
        av = self.freshen(av)
        expected_pubdate = utils.ymd(utils.todt(self.ajson['article']['published']))
        self.assertEqual(expected_pubdate, utils.ymd(av.datetime_published))

    def test_article_publish_v2(self):
        "an unpublished vs article can be successfully published"
        _, _, av = ajson_ingestor.ingest(self.ajson)
        self.assertEqual(models.Journal.objects.count(), 1)
        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        self.assertFalse(av.published())

        ajson_ingestor.publish(self.msid, self.version)
        av = self.freshen(av)
        self.assertTrue(av.published())

        # modify to a v2 and publish
        self.ajson['article']['version'] = 2
        del self.ajson['article']['published']
        _, _, av2 = ajson_ingestor.ingest_publish(self.ajson)

        av2 = self.freshen(av2)
        self.assertTrue(av2.published())
        self.assertEqual(utils.ymd(datetime.now()), utils.ymd(av2.datetime_published))
        

    def test_article_publish_fails_if_already_published(self):
        "a published article cannot be published again"
        _, _, av = ajson_ingestor.ingest(self.ajson)
        av = ajson_ingestor.publish(self.msid, self.version)
        av = self.freshen(av)
        self.assertTrue(av.published())

        # publish again
        self.assertRaises(StateError, ajson_ingestor.publish, self.msid, self.version)

    def test_article_publish_succeeds_for_published_article_if_forced(self):
        "publication of an already published article can occur only if forced"
        _, _, av = ajson_ingestor.ingest(self.ajson)
        av = ajson_ingestor.publish(self.msid, self.version)
        av = self.freshen(av)
        expected_pubdate = utils.ymd(utils.todt(self.ajson['article']['published']))
        self.assertEqual(expected_pubdate, utils.ymd(av.datetime_published))

        # publish again, no changes to pubdate expected
        av = ajson_ingestor.publish(self.msid, self.version, force=True)
        av = self.freshen(av)
        self.assertEqual(expected_pubdate, utils.ymd(av.datetime_published))

        # ingest new pubdate, force publication
        new_pubdate = utils.todt('2016-01-01')
        self.ajson['article']['published'] = new_pubdate
        ajson_ingestor.ingest_publish(self.ajson, force=True)
        av = self.freshen(av)
        self.assertEqual(utils.ymd(new_pubdate), utils.ymd(av.datetime_published))

    def test_out_of_sequence_publish_fails(self):
        "attempting to ingest an article with a version greater than another *published* version fails"
        # ingest and publish a v1
        _, _, av = ajson_ingestor.ingest(self.ajson) # v1
        ajson_ingestor.publish(self.msid, self.version)

        # now attempt to ingest a v3
        self.ajson['article']['version'] = 3
        self.assertRaises(StateError, ajson_ingestor.ingest, self.ajson)

        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        av = self.freshen(av)
        self.assertEqual(av.version, 1) # assert the version hasn't changed

    def test_publish_fails_if_no_article(self):
        self.assertEqual(models.ArticleVersion.objects.count(), 0)
        self.assertRaises(StateError, ajson_ingestor.publish, self.msid, self.version)

    def test_publish_dry_run(self):
        "specifying a dry run does not commit changes to database"
        _, _, saved_av = ajson_ingestor.ingest(self.ajson) # do an actual ingest first
        unsaved_av = ajson_ingestor.publish(self.msid, self.version, dry_run=True)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        # ensure the article version stored has no published date
        models.ArticleVersion.objects.get(pk=saved_av.pk, datetime_published=None)
        # and that the object returned *does* have a datetime published
        self.assertTrue(unsaved_av.published())


class IngestPublish(BaseCase):
    def setUp(self):
        self.ajson_fixture1 = join(self.fixture_dir, 'ajson', 'elife.01968.json')
        self.ajson = json.load(open(self.ajson_fixture1, 'r'))

    def tearDown(self):
        pass

    def test_ingest_publish(self):
        "ensure the shortcut ingest_publish behaves as expected"
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

        _, _, av = ajson_ingestor.ingest_publish(self.ajson)

        self.assertEqual(models.Journal.objects.count(), 1)
        self.assertEqual(models.Article.objects.count(), 1)
        self.assertEqual(models.ArticleVersion.objects.count(), 1)

        av = self.freshen(av)
        self.assertEqual(av.version, 1)
        self.assertTrue(av.published())

    def test_ingest_publish_force(self):
        "we can do silent corrections/updates if we force it to"
        _, _, av = ajson_ingestor.ingest_publish(self.ajson)
        expected_title = 'pants-party'
        self.ajson['article']['title'] = expected_title
        _, _, av = ajson_ingestor.ingest_publish(self.ajson, force=True)
        av = self.freshen(av)
        self.assertEqual(av.title, expected_title)

    def test_ingest_publish_no_force(self):
        "attempting to do an update without force=True fails"
        # ingest once
        _, _, av = ajson_ingestor.ingest_publish(self.ajson)
        # attempt second ingest
        self.assertRaises(StateError, ajson_ingestor.ingest_publish, self.ajson)

    def test_ingest_publish_dry_run(self):
        "specifying a dry run does not commit changes to database"
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

        j, a, av = ajson_ingestor.ingest_publish(self.ajson, dry_run=True)

        # all counts are still zero
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

        # article version believes itself to be published
        self.assertTrue(av.published())


class CLI(BaseCase):
    def setUp(self):
        self.nom = 'ingest'
        self.msid = "01968"
        self.version = "1"
        self.ajson_fixture1 = join(self.fixture_dir, 'ajson', 'elife.01968.json')

    def tearDown(self):
        pass

    def call_command(self, *args, **kwargs):
        stdout = StringIO()
        try:
            kwargs['stdout'] = stdout
            call_command(*args, **kwargs)
        except SystemExit as err:
            return err.code, stdout
        self.fail("ingest script should always throw a systemexit()")

    def test_ingest_from_cli(self):
        "ingest script requires the --ingest flag and a source of data"
        args = [self.nom, '--ingest', '--id', self.msid, '--version', self.version, self.ajson_fixture1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)
        # article has been ingested
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        # message returned is json encoded with all the right keys and values
        result = json.loads(stdout.getvalue())
        self.assertTrue(utils.has_all_keys(result, ['status', 'id', 'datetime']))
        self.assertEqual(result['status'], 'ingested')
        # the date and time is roughly the same as right now, ignoring microseconds
        expected_datetime = utils.utcnow().isoformat()
        self.assertEqual(result['datetime'][:20], expected_datetime[:20])
        self.assertEqual(result['datetime'][-6:], expected_datetime[-6:])

    def test_publish_from_cli(self):
        args = [self.nom, '--ingest', '--id', self.msid, '--version', self.version, self.ajson_fixture1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)
        # article has been ingested
        self.assertEqual(models.ArticleVersion.objects.count(), 1)

        args = [self.nom, '--publish', '--id', self.msid, '--version', self.version]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)
        # ensure response is json
        result = json.loads(stdout.getvalue())
        self.assertTrue(utils.has_all_keys(result, ['status', 'id', 'datetime']))
        self.assertEqual(result['status'], 'published')

    def test_ingest_publish_from_cli(self):
        args = [self.nom, '--ingest+publish', '--id', self.msid, '--version', self.version, self.ajson_fixture1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)
        # article has been ingested
        av = models.ArticleVersion.objects.get(article__manuscript_id=self.msid, version=self.version)
        # article has been published
        self.assertTrue(av.published())
        # ensure response is json and well-formed
        result = json.loads(stdout.getvalue())
        self.assertTrue(utils.has_all_keys(result, ['status', 'id', 'datetime']))
        # ensure response data is correct
        self.assertEqual(result['status'], 'published')
        self.assertEqual(result['datetime'], av.datetime_published.isoformat())

    def test_ingest_publish_dry_run_from_cli(self):
        # ensure nothing exists
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

        args = [self.nom, '--ingest+publish', '--id', self.msid, '--version', self.version,
                self.ajson_fixture1, '--dry-run']
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

        # ensure nothing was created
        self.assertEqual(models.Journal.objects.count(), 0)
        self.assertEqual(models.Article.objects.count(), 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

        # ensure response is json and well-formed
        result = json.loads(stdout.getvalue())
        self.assertTrue(utils.has_all_keys(result, ['status', 'id', 'datetime', 'message']))
        # ensure response data is correct
        self.assertEqual(result['status'], 'published')

        ajson = json.load(open(self.ajson_fixture1, 'r'))
        self.assertEqual(result['datetime'][:19], ajson['article']['published'])
        self.assertEqual(result['message'], "(dry-run)")
