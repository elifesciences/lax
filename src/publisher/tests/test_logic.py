import json
from os.path import join
from .base import BaseCase
from publisher import logic, ajson_ingestor, models, eif_ingestor

class TestLogic0(BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        import_all = [
            '00353.1', # discussion, VOR

            '00385.1', # commentary, VOR

            '01328.1', # correction, VOR

            '02619.1', # editorial, VOR

            '03401.1', # research, POA
            '03401.2', # POA
            '03401.3', # VOR

            '03665.1', # research, VOR

            '06250.1', # research, POA
            '06250.2', # POA
            '06250.3', # VOR

            '07301.1', # research, VOR

            '08025.1', # research, POA
            '08025.2', # VOR

            '09571.1', # research, POA
        ]
        for subdir in import_all:
            fname = subdir.replace('.', '-v')
            fname = "elife-%s.json" % fname
            path = join(self.fixture_dir, 'ppp', subdir, fname)
            eif_ingestor.import_article_from_json_path(self.journal, path)

        self.vor_version_count = 9
        self.poa_version_count = 6
        self.total_version_count = self.vor_version_count + self.poa_version_count

        self.poa_art_count = 1
        self.vor_art_count = 9
        self.total_art_count = self.poa_art_count + self.vor_art_count

        self.research_art_count = 6

    def test_latest_article_version_list(self):
        "ensure only the latest versions of the articles are returned"
        self.assertEqual(self.total_version_count, models.ArticleVersion.objects.count())

        total, latest = logic.latest_article_version_list()
        self.assertEqual(len(latest), self.total_art_count)
        self.assertEqual(len(latest), models.Article.objects.count())

        latest_idx = {obj.article.manuscript_id: obj for obj in latest}
        expected_latest = [
            (353, 1),
            (385, 1),
            (1328, 1),
            (2619, 1),
            (3401, 3),
            (3665, 1),
            (6250, 3),
            (7301, 1),
            (8025, 2),
            (9571, 1)
        ]
        for msid, v in expected_latest:
            # throws a DoesNotExist if expected not in latest resultset
            self.assertEqual(latest_idx[msid].version, v)

    def test_latest_article_version_list_wrapper(self):
        unpublish_these = [
            (9571, 1)
        ]
        for msid, version in unpublish_these:
            self.unpublish(msid, version)

        wrapper_total, wrapper_results = logic.latest_article_version_list(only_published=False)
        total, results = logic.latest_unpublished_article_versions()
        self.assertEqual(wrapper_total, total)
        # checks the items as well as the length
        # https://docs.python.org/3/library/unittest.html?highlight=assertcountequal#unittest.TestCase.assertCountEqual
        self.assertCountEqual(wrapper_results, results)

    def test_latest_article_version_list_only_unpublished(self):
        "ensure only the latest versions of the articles are returned when unpublished versions exist"
        self.assertEqual(self.total_version_count, models.ArticleVersion.objects.count())

        unpublish_these = [
            (3401, 3),
            (6250, 3),
            (8025, 2),
            (9571, 1)
        ]
        for msid, version in unpublish_these:
            self.unpublish(msid, version)

        total, results = logic.latest_article_version_list(only_published=False) # THIS IS THE IMPORTANT BIT
        total, results = logic.latest_unpublished_article_versions()

        self.assertEqual(len(results), self.total_art_count)
        self.assertEqual(len(results), models.Article.objects.count())

        result_idx = {obj.article.manuscript_id: obj for obj in results}
        expected_result = [
            (353, 1),
            (385, 1),
            (1328, 1),
            (2619, 1),
            (3401, 3),
            (3665, 1),
            (6250, 3),
            (7301, 1),
            (8025, 2),
            (9571, 1)
        ]
        for msid, v in expected_result:
            # throws a DoesNotExist if expected not in latest resultset
            self.assertEqual(result_idx[msid].version, v)

    def test_latest_article_version_list_with_published(self):
        "ensure only the latest versions of the articles are returned when unpublished versions exist"
        self.assertEqual(self.total_version_count, models.ArticleVersion.objects.count())

        unpublish_these = [
            (3401, 3),
            (6250, 3),
            (8025, 2),
            (9571, 1)
        ]
        for msid, version in unpublish_these:
            self.unpublish(msid, version)

        total, latest = logic.latest_article_version_list(only_published=True) # THIS IS THE IMPORTANT BIT
        latest_idx = {obj.article.manuscript_id: obj for obj in latest}

        self.assertEqual(len(latest), self.total_art_count - 1) # we remove 9571

        expected_latest = [
            (353, 1),
            (385, 1),
            (1328, 1),
            (2619, 1),
            (3401, 2), # from 3 to 2
            (3665, 1),
            (6250, 2), # from 3 to 2
            (7301, 1),
            (8025, 1), # from 2 to 1
            #(9571, 1) # from 1 to None
        ]
        for msid, expected_version in expected_latest:
            try:
                av = latest_idx[msid]
                self.assertEqual(av.version, expected_version)
            except:
                print('failed on', msid, 'version', expected_version)
                raise


class TestLogic(BaseCase):
    def setUp(self):
        ingest_these = [
            "elife-01968-v1.xml.json",
            "elife-16695-v1.xml.json",
            "elife-16695-v2.xml.json",
            "elife-16695-v3.xml.json"
        ]
        ajson_dir = join(self.fixture_dir, 'ajson')
        for ingestable in ingest_these:
            path = join(ajson_dir, ingestable)
            ajson_ingestor.ingest_publish(json.load(open(path, 'r')))
        self.msid1 = 1968
        self.msid2 = 16695

    def tearDown(self):
        pass

    def test_latest_article_versions(self):
        # see class `TestLogic0` (above) and `test_rss.py`
        pass

    def test_article_version_list(self):
        "all versions of an article are returned"
        expected_published_versions = 3
        avl = logic.article_version_list(self.msid2)
        self.assertEqual(avl.count(), expected_published_versions)

    def test_article_version_list_only_published(self):
        "all PUBLISHED versions of an article are returned"
        self.unpublish(self.msid2, version=3)
        expected_published_versions = 2
        avl = logic.article_version_list(self.msid2)
        self.assertEqual(avl.count(), expected_published_versions)

    def test_article_version_list_not_found(self):
        "an article doesn't exist if it has no article versions"
        fake_msid = 123
        self.assertRaises(models.Article.DoesNotExist, logic.article_version_list, fake_msid)

    def test_article_version(self):
        "the specific article version is returned"
        cases = [
            (self.msid1, 1),
            (self.msid2, 1),
            (self.msid2, 2),
            (self.msid2, 3)
        ]
        for msid, expected_version in cases:
            av = logic.article_version(msid, version=expected_version)
            self.assertEqual(av.article.manuscript_id, msid)
            self.assertEqual(av.version, expected_version)

    def test_article_version_only_published(self):
        "the specific PUBLISHED article version is returned"
        self.unpublish(self.msid2, version=3)
        self.assertRaises(models.ArticleVersion.DoesNotExist, logic.article_version, self.msid2, version=3)

    def test_article_version_not_found(self):
        "the right exception is thrown because they asked for a version specifically"
        fake_msid, version = 123, 1
        self.assertRaises(models.ArticleVersion.DoesNotExist, logic.article_version, fake_msid, version)

    def test_most_recent_article_version(self):
        "an article with three versions returns the highest version of the three"
        av = logic.most_recent_article_version(self.msid2)
        expected_version = 3
        self.assertEqual(av.version, expected_version)

    def test_most_recent_article_version_not_found(self):
        "a DNE exception is raised for a missing article"
        fake_msid = 123
        self.assertRaises(models.Article.DoesNotExist, logic.most_recent_article_version, fake_msid)

    def test_most_recent_article_version_unpublished(self):
        self.unpublish(self.msid2, version=3)
        self.assertEqual(models.ArticleVersion.objects.filter(article__manuscript_id=self.msid2).exclude(datetime_published=None).count(), 2)
        av = logic.most_recent_article_version(self.msid2)  # , only_published=False)
        self.assertEqual(av.version, 2)

    def test_article_json(self):
        pass

    def test_article_json_not_found(self):
        pass

    def test_article_snippet_json(self):
        pass

    def test_article_snippet_json_not_found(self):
        pass
