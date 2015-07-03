import os, time
from publisher import json_import as ingest, utils, models, logic

from base import BaseCase

import logging

logging.getLogger("").setLevel(logging.WARNING) # suppresses debug, info messages

class ImportArticleFromJSON(BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        #self.test_doc1 = os.path.join(self.this_dir, 'fixtures/test-doc.txt')
        #self.test_doc1_name = 'fixtures/test-doc.txt'
        doc = 'elife00005.xml.json'
        self.json_fixture = os.path.join(self.this_dir, 'fixtures', doc)

    def tearDown(self):
        pass

    def test_article_created(self):
        "an article can be imported from JSON"
        self.assertEqual(0, models.Article.objects.count())
        ingest.import_article(self.journal, self.json_fixture)
        self.assertEqual(1, models.Article.objects.count())

    def test_article_data(self):
        expected_data = {
            'title':  "Molecular architecture of human polycomb repressive complex 2",
            'version': 1,
            'doi': "10.7554/eLife.00005",
            'journal': self.journal,
        }
        article = ingest.import_article(self.journal, self.json_fixture)
        for attr, expected_value in expected_data.items():
            self.assertEqual(getattr(article, attr), expected_value)
