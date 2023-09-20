import json
from os.path import join
from . import base
from publisher import logic, ajson_ingestor, models, utils, relation_logic


class One(base.BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        import_all = [
            "00353.1",  # discussion, VOR
            "00385.1",  # commentary, VOR
            "01328.1",  # correction, VOR
            "02619.1",  # editorial, VOR
            "03401.1",  # research, POA
            "03401.2",  # POA
            "03401.3",  # VOR
            "03665.1",  # research, VOR
            "06250.1",  # research, POA
            "06250.2",  # POA
            "06250.3",  # VOR
            "07301.1",  # research, VOR
            "08025.1",  # research, POA
            "08025.2",  # VOR
            "09571.1",  # research, POA
        ]
        for subdir in import_all:
            fname = subdir.replace(".", "-v")
            fname = "elife-%s.xml.json" % fname
            path = join(self.fixture_dir, "ppp2", fname)
            ajson_ingestor.ingest_publish(self.load_ajson(path))  # strip relations

        self.vor_version_count = 9
        self.poa_version_count = 6
        self.total_version_count = self.vor_version_count + self.poa_version_count

        self.poa_art_count = 1
        self.vor_art_count = 9
        self.total_art_count = self.poa_art_count + self.vor_art_count

    def test_latest_article_version_list(self):
        "ensure only the latest versions of the articles are returned"
        self.assertEqual(
            self.total_version_count, models.ArticleVersion.objects.count()
        )

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
            (9571, 1),
        ]
        for msid, v in expected_latest:
            # throws a DoesNotExist if expected not in latest resultset
            self.assertEqual(latest_idx[msid].version, v)

    def test_latest_article_version_list_wrapper(self):
        unpublish_these = [(9571, 1)]
        for msid, version in unpublish_these:
            self.unpublish(msid, version)

        wrapper_total, wrapper_results = logic.latest_article_version_list(
            only_published=False
        )
        total, results = logic.latest_unpublished_article_versions()
        self.assertEqual(wrapper_total, total)
        # checks the items as well as the length
        # https://docs.python.org/3/library/unittest.html?highlight=assertcountequal#unittest.TestCase.assertCountEqual
        self.assertCountEqual(wrapper_results, results)

    def test_latest_article_version_list_only_unpublished(self):
        "ensure only the latest versions of the articles are returned when unpublished versions exist"
        self.assertEqual(
            self.total_version_count, models.ArticleVersion.objects.count()
        )

        unpublish_these = [(3401, 3), (6250, 3), (8025, 2), (9571, 1)]
        for msid, version in unpublish_these:
            self.unpublish(msid, version)

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
            (9571, 1),
        ]
        for msid, v in expected_result:
            # throws a DoesNotExist if expected not in latest resultset
            self.assertEqual(result_idx[msid].version, v)

    def test_latest_article_version_list_with_published(self):
        "ensure only the latest versions of the articles are returned when unpublished versions exist"
        self.assertEqual(
            self.total_version_count, models.ArticleVersion.objects.count()
        )

        unpublish_these = [(3401, 3), (6250, 3), (8025, 2), (9571, 1)]
        for msid, version in unpublish_these:
            self.unpublish(msid, version)

        total, latest = logic.latest_article_version_list(
            only_published=True
        )  # THIS IS THE IMPORTANT BIT
        latest_idx = {obj.article.manuscript_id: obj for obj in latest}

        self.assertEqual(len(latest), self.total_art_count - 1)  # we remove 9571

        expected_latest = [
            (353, 1),
            (385, 1),
            (1328, 1),
            (2619, 1),
            (3401, 2),  # from 3 to 2
            (3665, 1),
            (6250, 2),  # from 3 to 2
            (7301, 1),
            (8025, 1),  # from 2 to 1
            # (9571, 1) # from 1 to None
        ]
        for msid, expected_version in expected_latest:
            try:
                av = latest_idx[msid]
                self.assertEqual(av.version, expected_version)
            except BaseException:
                print("failed on", msid, "version", expected_version)
                raise


class Two(base.BaseCase):
    def setUp(self):
        ingest_these = [
            "elife-01968-v1.xml.json",
            "elife-16695-v1.xml.json",
            "elife-16695-v2.xml.json",
            "elife-16695-v3.xml.json",
        ]
        ajson_dir = join(self.fixture_dir, "ajson")
        for ingestable in ingest_these:
            path = join(ajson_dir, ingestable)
            ajson_ingestor.ingest_publish(json.load(open(path, "r")))
        self.msid1 = 1968
        self.msid2 = 16695

    def tearDown(self):
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
        self.assertRaises(
            models.Article.DoesNotExist, logic.article_version_list, fake_msid
        )

    def test_article_version(self):
        "the specific article version is returned"
        cases = [(self.msid1, 1), (self.msid2, 1), (self.msid2, 2), (self.msid2, 3)]
        for msid, expected_version in cases:
            av = logic.article_version(msid, version=expected_version)
            self.assertEqual(av.article.manuscript_id, msid)
            self.assertEqual(av.version, expected_version)

    def test_article_version_only_published(self):
        "the specific PUBLISHED article version is returned"
        self.unpublish(self.msid2, version=3)
        self.assertRaises(
            models.ArticleVersion.DoesNotExist,
            logic.article_version,
            self.msid2,
            version=3,
        )

    def test_article_version_not_found(self):
        "the right exception is thrown because they asked for a version specifically"
        fake_msid, version = 123, 1
        self.assertRaises(
            models.ArticleVersion.DoesNotExist,
            logic.article_version,
            fake_msid,
            version,
        )

    def test_most_recent_article_version(self):
        "an article with three versions returns the highest version of the three"
        av = logic.most_recent_article_version(self.msid2)
        expected_version = 3
        self.assertEqual(av.version, expected_version)

    def test_most_recent_article_version_not_found(self):
        "a DNE exception is raised for a missing article"
        fake_msid = 123
        self.assertRaises(
            models.Article.DoesNotExist, logic.most_recent_article_version, fake_msid
        )

    def test_most_recent_article_version_unpublished(self):
        self.unpublish(self.msid2, version=3)
        self.assertEqual(
            models.ArticleVersion.objects.filter(article__manuscript_id=self.msid2)
            .exclude(datetime_published=None)
            .count(),
            2,
        )
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


class ArticleHistoryV1(base.BaseCase):
    def setUp(self):
        ingest_these = ["elife-16695-v1.xml.json"]  # research article
        ajson_dir = join(self.fixture_dir, "ajson")
        for ingestable in ingest_these:
            path = join(ajson_dir, ingestable)
            ajson_ingestor.ingest_publish(json.load(open(path, "r")))
        self.msid = 16695

    def tearDown(self):
        pass

    def test_certain_articles_dont_get_accepted_received_dates(self):
        "received and accepted dates are not returned for certain article types"
        resp = logic.article_version_history__v1(self.msid)
        self.assertTrue("received" in resp)
        self.assertTrue("accepted" in resp)

        for extype in logic.EXCLUDE_RECEIVED_ACCEPTED_DATES:
            models.Article.objects.filter(manuscript_id=self.msid).update(type=extype)
            resp = logic.article_version_history__v1(self.msid)
            self.assertTrue("received" not in resp)
            self.assertTrue("accepted" not in resp)


class ArticleHistoryV2(base.BaseCase):
    def setUp(self):
        self.msid = 16695
        path = join(self.fixture_dir, "ajson", "elife-16695-v1.xml.json")
        fixture = json.load(open(path, "r"))
        preprint = {
            "status": "preprint",
            "description": "This manuscript was published as a preprint at bioRxiv.",
            "uri": "https://www.biorxiv.org/content/10.1101/2019.08.22.6666666v1",
            "date": "2019-02-15T00:00:00Z",
        }
        fixture["article"]["-history"]["preprint"] = preprint
        ajson_ingestor.ingest_publish(fixture)

    def test_preprints_returned(self):
        resp = logic.article_version_history__v2(self.msid)
        self.assertEqual(len(resp["versions"]), 2)
        expected = {
            "status": "preprint",
            "description": "This manuscript was published as a preprint at bioRxiv.",
            "uri": "https://www.biorxiv.org/content/10.1101/2019.08.22.6666666v1",
            "date": utils.todt("2019-02-15T00:00:00Z"),
        }
        self.assertEqual(resp["versions"][0], expected)

    def test_certain_articles_dont_get_accepted_received_dates(self):
        "received and accepted dates are not returned for certain article types"
        resp = logic.article_version_history__v2(self.msid)
        self.assertTrue("received" in resp)
        self.assertTrue("accepted" in resp)

        for extype in logic.EXCLUDE_RECEIVED_ACCEPTED_DATES:
            models.Article.objects.filter(manuscript_id=self.msid).update(type=extype)
            resp = logic.article_version_history__v2(self.msid)
            self.assertTrue("received" not in resp)
            self.assertTrue("accepted" not in resp)


class RelationshipLogic(base.BaseCase):
    def setUp(self):
        ingest_these = [
            "elife-01968-v1.xml.json",  # => 01749
            "elife-16695-v1.xml.json",  # => []
            # "elife-16695-v2.xml.json",
            "elife-20125-v1.xml.json",  # poa
            # "elife-16695-v3.xml.json"
        ]
        ajson_dir = join(self.fixture_dir, "ajson")
        for ingestable in ingest_these:
            path = join(ajson_dir, ingestable)
            data = json.load(open(path, "r"))
            # remove these values here so they don't interfere in creation
            utils.delall(
                data, ["-related-articles-internal", "-related-articles-external"]
            )
            ajson_ingestor.ingest_publish(data)

        self.msid1 = 1968
        self.msid2 = 16695
        self.msid3 = 20125

        self.av = models.ArticleVersion.objects.get(
            article__manuscript_id=self.msid1, version=1
        )
        self.a = models.Article.objects.get(
            manuscript_id=self.msid2
        )  # note: no version information

    def test_relationship_data(self):
        "we expect to see the article snippet of the related article"
        create_relationships = [(self.msid1, [self.msid2])]  # 1 => 2
        base._relate_using_msids(create_relationships)

        av1 = self.av
        av2 = models.ArticleVersion.objects.get(article__manuscript_id=self.msid2)

        # forwards
        self.assertEqual(
            [logic.article_snippet_json(av2)], logic.relationships(self.msid1)
        )
        # backwards
        self.assertEqual(
            [logic.article_snippet_json(av1)], logic.relationships(self.msid2)
        )

    def test_relationship_data2(self):
        "we expect to see the article snippet of the relationed article and external citations"
        create_relationships = [(self.msid1, [self.msid2])]  # 1 => 2
        base._relate_using_msids(create_relationships)

        av1 = self.av
        av2 = models.ArticleVersion.objects.get(article__manuscript_id=self.msid2)

        external_relation = {
            "type": "external-article",
            "articleTitle": "Tumour micro-environment elicits innate resistance to RAF inhibitors through HGF secretion",
            "journal": "Nature",
            "authorLine": "- R Straussman\n- T Morikawa\n- K Shee\n- M Barzily-Rokni\n- ZR Qian\n- J Du\n- A Davis\n- MM Mongare\n- J Gould\n- DT Frederick\n- ZA Cooper\n- PB Chapman\n- DB Solit\n- A Ribas\n- RS Lo\n- KT Flaherty\n- S Ogino\n- JA Wargo\n- TR Golub",
            "uri": "https://doi.org/10.1038/nature11183",
        }
        relation_logic.relate_using_citation_list(av1, [external_relation])
        relation_logic.relate_using_citation_list(av2, [external_relation])

        # forwards
        expected = [external_relation, logic.article_snippet_json(av2)]
        self.assertEqual(expected, logic.relationships(self.msid1))

        # backwards
        expected = [external_relation, logic.article_snippet_json(av1)]
        self.assertEqual(expected, logic.relationships(self.msid2))
