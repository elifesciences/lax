from mock import Mock, patch
import json
from os.path import join
from . import base
from publisher import models, utils, ajson_ingestor, codes
from django.test import override_settings

class DryRun(base.BaseCase):
    def setUp(self):
        self.nom = 'ingest'
        self.msid = "16695"
        self.ajson_fixture_v1 = join(self.fixture_dir, 'ajson', 'elife-16695-v1.xml.json')
        self.ajson_fixture_v2 = join(self.fixture_dir, 'ajson', 'elife-16695-v2.xml.json')

    def tearDown(self):
        pass

    def test_validate_from_cli(self):
        "an dry ingest can be passed without error"
        args = [self.nom, '--ingest', '--dry-run', '--id', self.msid, '--version', 1, self.ajson_fixture_v1]
        errcode, stdout = self.call_command(*args)
        # there shouldn't be anything wrong with this fixture
        self.assertEqual(errcode, 0)

    def test_validate_doesnt_create_anything(self):
        "a dry ingest doesn't create any articles"
        args = [self.nom, '--ingest', '--dry-run', '--id', self.msid, '--version', 1, self.ajson_fixture_v1]
        self.call_command(*args)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

    def test_validate_non_existant_av(self):
        "a dry ingest can be done for a non-existant article version"
        ajson = json.load(open(self.ajson_fixture_v1, 'r'))
        ajson_ingestor.ingest_publish(ajson) # *v1*
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        args = [self.nom, '--ingest', '--dry-run', '--id', self.msid, '--version', 2, self.ajson_fixture_v2] # *v2*
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 1) # still just one

    def test_validate_with_force_flag(self):
        "a dry ingest can be given a force flag"
        args = [self.nom, '--ingest', '--dry-run', '--id', self.msid, '--version', 1, '--force', self.ajson_fixture_v1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

    def test_validate_forced_action(self):
        "a dry ingest can be sent with a force flag on existing article to test validity of a silent correction"
        # article exists
        ajson = json.load(open(self.ajson_fixture_v1, 'r'))
        ajson['article']['foo'] = 'bar' # avoid hash check
        ajson_ingestor.ingest_publish(ajson)
        # a silent correction happens without problems
        args = [self.nom, '--ingest', '--dry-run', '--id', self.msid, '--version', 1, '--force', self.ajson_fixture_v1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

    def test_validate_without_force_flag(self):
        "an invalid dry ingest fails obviously"
        # article exists
        ajson = json.load(open(self.ajson_fixture_v1, 'r'))
        ajson_ingestor.ingest_publish(ajson)
        # attempt validation of given data
        args = [self.nom, '--ingest', '--dry-run', '--id', self.msid, '--version', 1, self.ajson_fixture_v1] # no force flag present
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 1) # 1 = error
        # error resp has a bucket of info
        resp = json.loads(stdout)
        self.assertTrue(utils.has_all_keys(resp, ['code', 'message', 'comment', 'trace']))

class Errors(base.BaseCase):
    def setUp(self):
        self.nom = 'ingest'
        self.msid = "16695"
        self.ajson_fixture_v1 = join(self.fixture_dir, 'ajson', 'elife-16695-v1.xml.json')
        self.ajson_fixture_v2 = join(self.fixture_dir, 'ajson', 'elife-16695-v2.xml.json')

    def tearDown(self):
        pass

    def test_error_response(self):
        "errors exit correctly and responses are structured correctly"
        args = [self.nom, '--ingest', '--dry-run', '--id', self.msid, '--version', 2, self.ajson_fixture_v2]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 1) # 1 = error

        resp = json.loads(stdout)

        # 2017-12-20: test changed from expecting an 'INVALID' response to
        # expecting a 'DOES NOT EXIST' response as order of checks changed.

        # a simple error identifier
        self.assertEqual(resp['code'], codes.PREVIOUS_VERSION_DNE)
        # an explanation of the error code
        self.assertEqual(resp['comment'], codes.explain(codes.PREVIOUS_VERSION_DNE))
        # keys called 'message' and 'trace' exist with values
        self.assertTrue(resp['message']) # a friendly error message
        self.assertTrue(resp['trace']) # a traceback for developers


class CLI(base.BaseCase):
    def setUp(self):
        self.nom = 'ingest'
        self.msid = "01968"
        self.version = "1"
        self.ajson_fixture1 = join(self.fixture_dir, 'ajson', 'elife-01968-v1.xml.json')

    def tearDown(self):
        pass

    def test_ingest_from_cli(self):
        "ingest script requires the --ingest flag and a source of data"
        args = [self.nom, '--ingest', '--id', self.msid, '--version', self.version, self.ajson_fixture1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)
        # article has been ingested
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        # message returned is json encoded with all the right keys and values
        result = json.loads(stdout)
        self.assertTrue(utils.has_all_keys(result, ['status', 'id', 'datetime']))
        self.assertEqual(result['status'], 'ingested')
        # the date and time is roughly the same as right now, ignoring microseconds
        expected_datetime = utils.utcnow()
        actual_datetime = utils.todt(result['datetime'])
        delta = expected_datetime - actual_datetime
        threshold = 2 # seconds
        self.assertTrue(delta.seconds <= threshold)

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
        result = json.loads(stdout)
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
        result = json.loads(stdout)
        self.assertTrue(utils.has_all_keys(result, ['status', 'id', 'datetime']))
        # ensure response data is correct
        self.assertEqual(result['status'], 'published')
        self.assertEqual(result['datetime'], utils.ymdhms(av.datetime_published))

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
        result = json.loads(stdout)
        self.assertTrue(utils.has_all_keys(result, ['status', 'id', 'datetime', 'dry-run']))
        # ensure response data is correct
        self.assertEqual(result['status'], 'validated')
        self.assertEqual(result['dry-run'], True)

        ajson = json.load(open(self.ajson_fixture1, 'r'))
        self.assertEqual(result['datetime'], ajson['article']['published'])

    def test_ingest_identical_from_cli(self):
        "ingesting an article whose identical data already exists gives a 'success' response"
        args = [self.nom, '--ingest', '--id', self.msid, '--version', self.version, self.ajson_fixture1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

        dummy_dt = '2001-01-01T00:00:00Z'
        models.ArticleVersion.objects.all().update(datetime_record_updated=dummy_dt) # bypasses auto_now=True in field

        # do it again, same command, same data
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

        resp = json.loads(stdout)

        # attempting to ingest the same article twice results in the error being
        # swallowed and a simple 'ingested' status being returned
        self.assertEqual(resp['status'], 'ingested')
        # the date of the original ingest is returned
        self.assertEqual(resp['datetime'], dummy_dt)

    def test_forced_identical_ingest_from_cli_when_already_published(self):
        "forcing an ingest of a published article (backfill) when article data is identical returns a success response"
        # publish an article
        args = [self.nom, '--ingest+publish', '--id', self.msid, '--version', self.version, self.ajson_fixture1]
        self.call_command(*args)

        # fudge date
        dummy_dt = '2001-01-01T00:00:00Z'
        models.ArticleVersion.objects.all().update(datetime_record_updated=dummy_dt) # bypasses auto_now=True in field

        # force ingest the same article data
        args = [self.nom, '--ingest', '--id', self.msid, '--version', self.version, '--force', self.ajson_fixture1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

        resp = json.loads(stdout)

        # attempting to ingest the same article twice results in the error being
        # swallowed and a simple 'ingested' status being returned
        self.assertEqual(resp['status'], 'ingested')
        # the date of the original ingest is returned
        self.assertEqual(resp['datetime'], dummy_dt)


class MultiCLI(base.TransactionBaseCase):
    def setUp(self):
        self.nom = 'ingest'

    @override_settings(DEBUG=False, ENABLE_RELATIONS=False) # get past the early return in aws_events
    def test_multiple_ingest_from_cli(self):
        "a directory of article-json can be ingested"

        expected_artv_count = 14
        expected_art_count = 7

        # ensure all the articles + versions exist before we do a multiprocess run
        mock = Mock()
        with patch('publisher.aws_events.event_bus_conn', return_value=mock):
            args = [self.nom, '--ingest+publish', '--serial', '--dir', join(self.fixture_dir, 'ajson')]
            errcode, stdout = self.call_command(*args)
            self.assertEqual(errcode, 0) # nothing failed

            # articles have been ingested
            self.assertEqual(models.Article.objects.count(), expected_art_count)
            self.assertEqual(models.ArticleVersion.objects.count(), expected_artv_count)

            # publish is called once per article (not article version)
            self.assertEqual(expected_art_count, mock.publish.call_count)

        # tweak article data to avoid failing hashcheck
        for av in models.ArticleVersion.objects.all():
            av.article_json_hash = 'pants'
            av.save()

        # simulate a backfill
        mock = Mock()
        with patch('publisher.aws_events.event_bus_conn', return_value=mock):
            args = [self.nom, '--ingest', '--force', '--dir', join(self.fixture_dir, 'ajson')]
            errcode, stdout = self.call_command(*args)
            self.assertEqual(errcode, 0) # nothing failed

            # publish is called once per article (not article version) despite multithreading
            self.assertEqual(expected_art_count, mock.publish.call_count)

    @override_settings(DEBUG=False, ENABLE_RELATIONS=False) # get past the early return in aws_events
    def test_multiple_identical_ingest_from_cli(self):
        "a directory of article-json can be ingested many times with events only sent once"

        expected_artv_count = 14
        expected_call_count = 7 # 1 for each article

        # ensure all the articles + versions exist before we do a multiprocess run
        mock = Mock()
        with patch('publisher.aws_events.event_bus_conn', return_value=mock):
            args = [self.nom, '--ingest+publish', '--serial', '--dir', join(self.fixture_dir, 'ajson')]
            errcode, _ = self.call_command(*args)
            self.assertEqual(errcode, 0) # nothing failed
            self.assertEqual(models.ArticleVersion.objects.count(), expected_artv_count)

            # publish is called once per article (not article version)
            self.assertEqual(expected_call_count, mock.publish.call_count)

            # simulate a backfill
            args = [self.nom, '--ingest', '--force', '--dir', join(self.fixture_dir, 'ajson')]
            errcode, stdout = self.call_command(*args)
            self.assertEqual(errcode, 0) # nothing failed

            # publish is not called again (data hasn't changed)
            self.assertEqual(expected_call_count, mock.publish.call_count)
