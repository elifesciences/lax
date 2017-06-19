import json
from os.path import join
from .base import BaseCase
from publisher import models, utils, ajson_ingestor

class One(BaseCase):
    def setUp(self):
        self.nom = 'ingest'
        self.msid = "16695"
        self.ajson_fixture_v1 = join(self.fixture_dir, 'ajson', 'elife-16695-v1.xml.json')
        self.ajson_fixture_v2 = join(self.fixture_dir, 'ajson', 'elife-16695-v2.xml.json')

    def tearDown(self):
        pass

    def test_validate_from_cli(self):
        "a VALIDATE message can be passed without error"
        args = [self.nom, '--validate', '--id', self.msid, '--version', 1, self.ajson_fixture_v1]
        errcode, stdout = self.call_command(*args)
        # there shouldn't be anything wrong with this fixture
        self.assertEqual(errcode, 0)

    def test_validate_doesnt_create_anything(self):
        "a VALIDATE message can be passed without creating any articles"
        args = [self.nom, '--validate', '--id', self.msid, '--version', 1, self.ajson_fixture_v1]
        self.call_command(*args)
        self.assertEqual(models.ArticleVersion.objects.count(), 0)

    def test_validate_non_existant_av(self):
        "a VALIDATE message can be passed for a non-existant version of an article"
        ajson = json.load(open(self.ajson_fixture_v1, 'r'))
        ajson_ingestor.ingest_publish(ajson) # *v1*
        self.assertEqual(models.ArticleVersion.objects.count(), 1)
        args = [self.nom, '--validate', '--id', self.msid, '--version', 2, self.ajson_fixture_v2] # *v2*
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)
        self.assertEqual(models.ArticleVersion.objects.count(), 1) # still just one

    def test_validate_with_force_flag(self):
        "a VALIDATE message can be sent with a force flag"
        args = [self.nom, '--validate', '--id', self.msid, '--version', 1, '--force', self.ajson_fixture_v1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

    def test_validate_forced_action(self):
        "a VALIDATE message can be sent with a force flag to test validity of a silent correction"
        # article exists
        ajson = json.load(open(self.ajson_fixture_v1, 'r'))
        ajson_ingestor.ingest_publish(ajson)
        # a silent correction happens without problems
        args = [self.nom, '--validate', '--id', self.msid, '--version', 1, '--force', self.ajson_fixture_v1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

    def test_validate_without_force_flag(self):
        "a VALIDATE message fails obviously"
        # article exists
        ajson = json.load(open(self.ajson_fixture_v1, 'r'))
        ajson_ingestor.ingest_publish(ajson)
        # attempt validation of given data
        args = [self.nom, '--validate', '--id', self.msid, '--version', 1, self.ajson_fixture_v1]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 1) # 1=error


class CLI(BaseCase):
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
        self.assertTrue(utils.has_all_keys(result, ['status', 'id', 'datetime', 'message']))
        # ensure response data is correct
        self.assertEqual(result['status'], 'published')

        ajson = json.load(open(self.ajson_fixture1, 'r'))
        self.assertEqual(result['datetime'], ajson['article']['published'])
        self.assertEqual(result['message'], "(dry-run)")
