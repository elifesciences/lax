from os.path import join
import json
from . import base
from publisher import ajson_ingestor, models, relation_logic

class R1(base.BaseCase):
    def setUp(self):
        ingest_these = [
            "elife-01968-v1.xml.json",
            "elife-16695-v1.xml.json",
            "elife-16695-v2.xml.json",
            "elife-20125-v1.xml.json",
            #"elife-16695-v3.xml.json"
        ]
        ajson_dir = join(self.fixture_dir, 'ajson')
        for ingestable in ingest_these:
            path = join(ajson_dir, ingestable)
            ajson_ingestor.ingest_publish(json.load(open(path, 'r')))

        self.msid1 = 1968
        self.msid2 = 16695
        self.msid3 = 20125

        self.av = models.ArticleVersion.objects.get(article__manuscript_id=self.msid1, version=1)
        self.a = models.Article.objects.get(manuscript_id=self.msid2) # note: no version information

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

    '''
    # possible business rule ...
    def test_relationship_cannot_be_created_with_self(self):
        "an ArticleVersion cannot have a relationship with it's parent."
        pass
    '''

    def test_create_many_relations_using_msids(self):
        "relationships between an ArticleVersion and other articles can be created in bulk"
        relationship_list = relation_logic.relate_using_msid_list(self.av, [self.msid2, self.msid3])
        self.assertEqual(2, models.ArticleVersionRelation.objects.count())
        for relationship in relationship_list:
            self.assertTrue(isinstance(relationship, models.ArticleVersionRelation))

    def test_replacing_relationships(self):
        # create a few relationships
        relation_logic.relate_using_msid_list(self.av, [self.msid2, self.msid3])
        self.assertEqual(2, models.ArticleVersionRelation.objects.count())

        # adding the same again and we'll still have 2
        relation_logic.relate_using_msid_list(self.av, [self.msid2])
        self.assertEqual(2, models.ArticleVersionRelation.objects.count())

        # adding the same again, but with replace=True, we'll have just 1
        relation_logic.relate_using_msid_list(self.av, [self.msid2], replace=True)
        self.assertEqual(1, models.ArticleVersionRelation.objects.count())
