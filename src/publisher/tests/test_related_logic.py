from os.path import join
import json, copy
from . import base
from publisher import ajson_ingestor, models, relation_logic, utils
from django.core.exceptions import ValidationError

class RelatedInternally(base.BaseCase):
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
            data = json.load(open(path, 'r'))
            # remove these values here so they don't interfere in creation
            utils.delall(data, ['-related-articles-internal', '-related-articles-external'])
            ajson_ingestor.ingest_publish(data)

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
        for relationship, msid in zip(relationship_list, [self.msid2, self.msid3]):
            self.assertTrue(isinstance(relationship, models.ArticleVersionRelation))
            self.assertEqual(relationship.articleversion, self.av)
            self.assertEqual(relationship.related_to.manuscript_id, msid)

    '''
    # removing previous relationships is now the responsibility of the ingestor
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
    '''

class RelatedExternally(base.BaseCase):
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
            data = json.load(open(path, 'r'))
            # remove these values here so they don't interfere in creation
            utils.delall(data, ['-related-articles-internal', '-related-articles-external'])
            ajson_ingestor.ingest_publish(data)

        self.msid1 = 1968
        self.msid2 = 16695
        self.msid3 = 20125

        self.av = models.ArticleVersion.objects.get(article__manuscript_id=self.msid1, version=1)
        self.a = models.Article.objects.get(manuscript_id=self.msid2) # note: no version information

        self.citation = {
            "type": "external-article",
            "articleTitle": "Transcriptional amplification in tumor cells with elevated c-Myc",
            "journal": "Cell",
            "authorLine": "C. Y. Lin et al",
            "uri": "https://doi.org/10.1016/j.cell.2012.08.026"
        }
        self.citation2 = copy.deepcopy(self.citation)
        self.citation2['uri'] = 'https://doi.org/10.0000/foo'

        self.bad_citation = copy.deepcopy(self.citation)
        self.bad_citation['uri'] = 'paaaants'

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
        self.assertRaises(ValidationError, relation_logic.associate, self.av, self.bad_citation) # not a uri
        self.assertRaises(AssertionError, relation_logic.associate, self.av, None) # not a dict
        self.assertRaises(AssertionError, relation_logic.associate, self.av, {}) # empty

    def test_create_many_external_relationships(self):
        self.assertEqual(0, models.ArticleVersionExtRelation.objects.count())
        relation_logic.relate_using_citation_list(self.av, [self.citation, self.citation2])
        self.assertEqual(2, models.ArticleVersionExtRelation.objects.count())

    def test_external_relationships_are_also_removed(self):
        relation_logic.associate(self.av, self.citation)
        self.assertEqual(1, models.ArticleVersionExtRelation.objects.count())
        relation_logic.remove_relationships(self.av)
        self.assertEqual(0, models.ArticleVersionExtRelation.objects.count())

class Ingest(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_relations_created_during_ingest(self):
        pass

    def test_relations_replaced_during_ingest(self):
        pass

class RelationList(base.BaseCase):
    def setUp(self):
        ingest_these = [
            "elife-01968-v1.xml.json",
            "elife-16695-v1.xml.json",
            "elife-20125-v1.xml.json",
        ]
        ajson_dir = join(self.fixture_dir, 'ajson')
        for ingestable in ingest_these:
            path = join(ajson_dir, ingestable)
            data = json.load(open(path, 'r'))
            # remove these values here so they don't interfere in creation
            utils.delall(data, ['-related-articles-internal', '-related-articles-external'])
            ajson_ingestor.ingest_publish(data)

        self.msid1 = 1968
        self.msid2 = 16695
        self.msid3 = 20125

        self.av = models.ArticleVersion.objects.get(article__manuscript_id=self.msid1, version=1)

    def tearDown(self):
        pass

    def _relate_using_msids(self, matrix):
        for target, msid_list in matrix:
            av = models.Article.objects.get(manuscript_id=target).latest_version
            relation_logic.relate_using_msid_list(av, msid_list)

    def _print_relations(self):
        for avr in models.ArticleVersionRelation.objects.all():
            print(avr)
            
    def test_relations_found_for_article(self):
        create_relationships = [
            (self.msid1, [self.msid2]), # 1 => 2
            (self.msid2, [self.msid3]), # 2 => 3
            (self.msid3, [self.msid1]), # 3 => 1
        ]
        self._relate_using_msids(create_relationships)

        expected_relationships = [
            (self.msid1, [self.msid2, self.msid3]), # 1 => [2, 3]
            (self.msid2, [self.msid3, self.msid1]), # 2 => [3, 1]
            (self.msid3, [self.msid1, self.msid2]), # 3 => [1, 2]
        ]

        #import pdb;pdb.set_trace() 
            
        #import IPython
        #IPython.embed()
            
        #import code; code.interact(local=locals())

        self._print_relations()
            
        for msid, expected_relations in expected_relationships:
            actual_relationships = relation_logic.internal_relationships_for_article(msid)
            #self.assertEqual(expected_relations, [r.related_to.manuscript_id for r in actual_relationships], \
            #                     "for %r I expected relations to %r" % (msid, expected_relations))

            self.assertEqual(expected_relations, [r.manuscript_id for r in actual_relationships])
            
    def test_reverse_relations_found_for_article(self):
        pass