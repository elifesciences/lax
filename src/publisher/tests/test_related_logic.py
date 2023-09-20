from os.path import join
import json, copy
from . import base
from publisher import ajson_ingestor, models, relation_logic, utils  # , logic
from django.core.exceptions import ValidationError


class RelatedInternally(base.BaseCase):
    def setUp(self):
        ingest_these = [
            "elife-01968-v1.xml.json",
            "elife-16695-v1.xml.json",
            "elife-16695-v2.xml.json",
            "elife-20125-v1.xml.json",
            # "elife-16695-v3.xml.json"
        ]
        ajson_dir = join(self.fixture_dir, "ajson")
        for ingestable in ingest_these:
            data = self.load_ajson(join(ajson_dir, ingestable))
            ajson_ingestor.ingest_publish(data)

        self.msid1 = 1968
        self.msid2 = 16695
        self.msid3 = 20125

        self.av = models.ArticleVersion.objects.get(
            article__manuscript_id=self.msid1, version=1
        )
        # note: no version information
        self.a = models.Article.objects.get(manuscript_id=self.msid2)

    def tearDown(self):
        pass

    def test_create_relation(self):
        "an ArticleVersion can be related to an Article (if both exist)"
        relationship = relation_logic.relate(self.av, self.a)
        self.assertTrue(isinstance(relationship, models.ArticleVersionRelation))

    def test_create_relation_is_idempotent(self):
        "creating a relationship is idempotent"
        for n in range(1, 10):
            relation_logic.relate(self.av, self.a)
            self.assertEqual(1, models.ArticleVersionRelation.objects.count())

    def test_create_relation_using_msid(self):
        "a relationship between an article version can be created with just an article msid"
        relationship = relation_logic.relate_using_msid(self.av, self.msid2)
        self.assertTrue(isinstance(relationship, models.ArticleVersionRelation))

    """
    # possible business rule ...
    def test_relationship_cannot_be_created_with_self(self):
        "an ArticleVersion cannot have a relationship with it's parent."
        pass
    """

    def test_create_many_relations_using_msids(self):
        "relationships between an ArticleVersion and other articles can be created in bulk"
        relationship_list = relation_logic.relate_using_msid_list(
            self.av, [self.msid2, self.msid3]
        )
        self.assertEqual(2, models.ArticleVersionRelation.objects.count())
        for relationship, msid in zip(relationship_list, [self.msid2, self.msid3]):
            self.assertTrue(isinstance(relationship, models.ArticleVersionRelation))
            self.assertEqual(relationship.articleversion, self.av)
            self.assertEqual(relationship.related_to.manuscript_id, msid)


class RelatedExternally(base.BaseCase):
    def setUp(self):
        ingest_these = [
            "elife-01968-v1.xml.json",
            "elife-16695-v1.xml.json",
            "elife-16695-v2.xml.json",
            "elife-20125-v1.xml.json",
            # "elife-16695-v3.xml.json"
        ]
        ajson_dir = join(self.fixture_dir, "ajson")
        for ingestable in ingest_these:
            data = self.load_ajson(join(ajson_dir, ingestable))
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

        self.citation = {
            "type": "external-article",
            "articleTitle": "Transcriptional amplification in tumor cells with elevated c-Myc",
            "journal": "Cell",
            "authorLine": "C. Y. Lin et al",
            "uri": "https://doi.org/10.1016/j.cell.2012.08.026",
        }
        self.citation2 = copy.deepcopy(self.citation)
        self.citation2["uri"] = "https://doi.org/10.0000/foo"

        self.bad_citation = copy.deepcopy(self.citation)
        self.bad_citation["uri"] = "paaaants"

    def tearDown(self):
        pass

    def test_create_external_relationship(self):
        "an article can be related to an external object"
        self.assertEqual(0, models.ArticleVersionExtRelation.objects.count())
        relationship = relation_logic.associate(self.av, self.citation)
        self.assertEqual(1, models.ArticleVersionExtRelation.objects.count())
        self.assertEqual(relationship.articleversion, self.av)

    def test_create_external_relationship_idempotent(self):
        "an article can be related to an external object"
        self.assertEqual(0, models.ArticleVersionExtRelation.objects.count())
        relation_logic.associate(self.av, self.citation)
        relation_logic.associate(self.av, self.citation)
        self.assertEqual(1, models.ArticleVersionExtRelation.objects.count())

    def test_external_relationship_data(self):
        self.assertRaises(
            ValidationError, relation_logic.associate, self.av, self.bad_citation
        )  # not a uri
        self.assertRaises(
            AssertionError, relation_logic.associate, self.av, None
        )  # not a dict
        self.assertRaises(
            AssertionError, relation_logic.associate, self.av, {}
        )  # empty

    def test_create_many_external_relationships(self):
        self.assertEqual(0, models.ArticleVersionExtRelation.objects.count())
        relation_logic.relate_using_citation_list(
            self.av, [self.citation, self.citation2]
        )
        self.assertEqual(2, models.ArticleVersionExtRelation.objects.count())

    def test_external_relationships_are_also_removed(self):
        relation_logic.associate(self.av, self.citation)
        self.assertEqual(1, models.ArticleVersionExtRelation.objects.count())
        relation_logic.remove_relationships(self.av)
        self.assertEqual(0, models.ArticleVersionExtRelation.objects.count())


class IngestPublish(base.BaseCase):
    def setUp(self):
        ingest_these = [
            "elife-04718-v1.xml.json",  # reverse relation to 13038
            "elife-13038-v1.xml.json",  # int relation to 04718
            "elife-13620-v1.xml.json",  # ext relation
        ]
        ajson_dir = join(self.fixture_dir, "relatedness")
        for ingestable in ingest_these:
            data = json.load(open(join(ajson_dir, ingestable), "r"))
            ajson_ingestor.ingest_publish(data)
        self.assertEqual(models.ArticleVersion.objects.count(), 3)

    def tearDown(self):
        pass

    def test_relations_created_during_ingest(self):
        self.assertEqual(1, models.ArticleVersionRelation.objects.count())  # 13038
        self.assertEqual(1, models.ArticleVersionExtRelation.objects.count())  # 13620

    def test_relations_replaced_during_ingest(self):
        data = json.load(
            open(join(self.fixture_dir, "relatedness", "elife-13038-v1.xml.json"))
        )
        # point to 13620
        data["article"]["-related-articles-internal"] = ["13620"]
        data["article"]["foo"] = "bar"  # tweak article data to avoid failing hashcheck
        ajson_ingestor.ingest(data, force=True)
        avr = models.ArticleVersionRelation.objects.all()
        self.assertEqual(1, avr.count())  # still have just the one relationship ...
        # and it's been updated
        self.assertEqual(
            avr[0].related_to, models.Article.objects.get(manuscript_id="13620")
        )

    def test_v1_relations_preserved_ingesting_v2(self):
        data = json.load(
            open(join(self.fixture_dir, "relatedness", "elife-13038-v1.xml.json"))
        )
        # point to 13620
        data["article"]["-related-articles-internal"] = ["13620"]
        data["article"]["version"] = 2
        ajson_ingestor.ingest(data)
        avr = models.ArticleVersionRelation.objects.all().order_by(
            "articleversion__version"
        )
        self.assertEqual(2, avr.count())  # two relations now
        for i, avr in enumerate(avr):
            self.assertEqual(avr.articleversion.version, i + 1)

    def test_ingest_fails_if_relations_nonexistant(self):
        "an article that is related to an article that doesn't exist cannot be ingested."
        models.ArticleVersionRelation.objects.all().delete()
        data = json.load(
            open(join(self.fixture_dir, "relatedness", "elife-13038-v1.xml.json"))
        )
        data["article"]["-related-articles-internal"] = ["42"]
        data["article"]["version"] = 2
        with self.settings(RELATED_ARTICLE_STUBS=False):
            self.assertRaises(utils.StateError, ajson_ingestor.ingest, data)
            avr = models.ArticleVersionRelation.objects.all()
            self.assertEqual(0, avr.count())

    def test_forced_ingest_passes_with_nonexistant_relations(self):
        "an article that is related to an article that doesn't exist cannot be ingested (unless forced)."
        models.ArticleVersionRelation.objects.all().delete()
        data = json.load(
            open(join(self.fixture_dir, "relatedness", "elife-13038-v1.xml.json"))
        )
        data["article"]["-related-articles-internal"] = ["42"]
        data["article"]["version"] = 2

        with self.settings(RELATED_ARTICLE_STUBS=False):
            ajson_ingestor.ingest(data, force=True)
            avr = models.ArticleVersionRelation.objects.all()
            self.assertEqual(0, avr.count())  # not created ...
            models.ArticleVersion.objects.get(
                article__manuscript_id=13038, version=2
            )  # ... but ingested

    def test_ingest_passes_and_creates_stubs_if_option_on(self):
        "an article that is related to an article that doesn't exist will have the related Article created as a stub."
        models.ArticleVersionRelation.objects.all().delete()
        data = json.load(
            open(join(self.fixture_dir, "relatedness", "elife-13038-v1.xml.json"))
        )
        data["article"]["-related-articles-internal"] = [42]
        data["article"]["version"] = 2

        with self.settings(RELATED_ARTICLE_STUBS=True):
            ajson_ingestor.ingest(data)
            avr = models.ArticleVersionRelation.objects.all()
            self.assertEqual(1, avr.count())  # relationship created ...
            models.ArticleVersion.objects.get(
                article__manuscript_id=13038, version=2
            )  # ... and av ingested
            models.Article.objects.get(manuscript_id=42)  # ... and stub created


class RelationList(base.BaseCase):
    def setUp(self):
        ingest_these = [
            "elife-01968-v1.xml.json",
            "elife-16695-v1.xml.json",
            "elife-20125-v1.xml.json",
        ]
        ajson_dir = join(self.fixture_dir, "ajson")
        for ingestable in ingest_these:
            data = self.load_ajson(join(ajson_dir, ingestable))
            ajson_ingestor.ingest_publish(data)

        self.msid1 = 1968
        self.msid2 = 16695
        self.msid3 = 20125

        self.av = models.ArticleVersion.objects.get(
            article__manuscript_id=self.msid1, version=1
        )

    def tearDown(self):
        pass

    def test_relations_found_for_article(self):
        create_relationships = [
            (self.msid1, [self.msid2]),  # 1 => 2
            (self.msid2, [self.msid3]),  # 2 => 3
            (self.msid3, [self.msid1]),  # 3 => 1
        ]
        relation_logic._relate_using_msids(create_relationships)

        expected_relationships = [
            (self.msid1, [self.msid2, self.msid3]),  # 1 => [2, 3]
            (self.msid2, [self.msid3, self.msid1]),  # 2 => [3, 1]
            (self.msid3, [self.msid1, self.msid2]),  # 3 => [1, 2]
        ]

        # relation_logic._print_relations()

        for msid, expected_relations in expected_relationships:
            av = models.Article.objects.get(manuscript_id=msid).latest_version
            actual_relationships = (
                relation_logic.internal_relationships_for_article_version(av)
            )
            self.assertCountEqual(
                expected_relations,
                [r.manuscript_id for r in actual_relationships],
                "for %r I expected relations to %r" % (msid, expected_relations),
            )

    def test_relations_found_for_article2(self):
        "no duplicates should exist when reverse relationships are made explicit"
        create_relationships = [
            (self.msid1, [self.msid2, self.msid3]),  # 1 => 2, 3
            (self.msid2, [self.msid3, self.msid1]),  # 2 => 3, 1
            (self.msid3, [self.msid1, self.msid2]),  # 3 => 1, 2
        ]
        relation_logic._relate_using_msids(create_relationships)

        expected_relationships = [
            (self.msid1, [self.msid2, self.msid3]),  # 1 => [2, 3]
            (self.msid2, [self.msid3, self.msid1]),  # 2 => [3, 1]
            (self.msid3, [self.msid1, self.msid2]),  # 3 => [1, 2]
        ]

        for msid, expected_relations in expected_relationships:
            av = models.Article.objects.get(manuscript_id=msid).latest_version
            actual_relationships = (
                relation_logic.internal_relationships_for_article_version(av)
            )
            self.assertCountEqual(
                expected_relations,
                [r.manuscript_id for r in actual_relationships],
                "for %r I expected relations to %r" % (msid, expected_relations),
            )

    def test_relation_data(self):
        "we expect to see the article object of the related article"
        create_relationships = [(self.msid1, [self.msid2])]  # 1 => 2
        relation_logic._relate_using_msids(create_relationships)

        av1 = self.av
        av2 = models.ArticleVersion.objects.get(article__manuscript_id=self.msid2)

        a1 = self.av.article
        a2 = models.Article.objects.get(manuscript_id=self.msid2)

        # forwards
        self.assertEqual(
            [a2], relation_logic.internal_relationships_for_article_version(av1)
        )
        # backwards
        self.assertEqual(
            [a1], relation_logic.internal_relationships_for_article_version(av2)
        )

    def test_reverse_relations_for_unpublished_article_not_returned(self):
        # an unpublished article may reference a published article
        # this would cause a backwards relationship to exist for the published article
        # the published article may then return an unpublished snippet
        pass

    def test_external_relations_found_for_article(self):
        pass
