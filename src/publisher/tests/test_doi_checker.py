import os
import base
import requests
from publisher import logic, ingestor, models

from unittest import skip

class DOICheck(base.BaseCase):
    def setUp(self):
        self.article_path = os.path.join(self.this_dir, 'fixtures/elife00005.xml.json')

    def tearDown(self):
        pass

    @skip("unfinished")
    def test_doi(self):
        art, ver = ingestor.import_article_from_json_path(logic.journal(), self.article_path)
        self.assertEqual(1, models.Article.objects.count())
        print logic.check_doi(art.doi)
        self.assertTrue(False)
