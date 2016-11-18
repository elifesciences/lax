from os.path import join
from mock import patch
from .base import BaseCase
from publisher import ajson_ingestor
import json

class CLI(BaseCase):
    def setUp(self):
        self.nom = 'check_article'
        self.msid_list = ["20125", "20105", "19264"] # 17267 17850 19083 18638 20143 21734 16578".split()

        ingest_these = [
            "dummyelife-20125-v1.xml.json", # poa
            "dummyelife-20125-v2.xml.json", # poa
            "dummyelife-20125-v3.xml.json", # vor

            "dummyelife-20105-v1.xml.json", # poa
            "dummyelife-20105-v2.xml.json", # poa
            "dummyelife-20105-v3.xml.json" # poa, UNPUBLISHED
        ]
        ajson_dir = join(self.fixture_dir, 'ajson')
        for ingestable in ingest_these:
            path = join(ajson_dir, ingestable)
            ajson_ingestor.ingest_publish(json.load(open(path, 'r')))

    def tearDown(self):
        pass

    @patch('publisher.management.commands.check_article.OUTPUT_DIR', join(BaseCase.fixture_dir, 'scrapy-cache'))
    def test_check_article(self):
        args = [self.nom, '--msid'] + self.msid_list
        errcode, stdout = self.call_command(*args)
        # stdout.getvalue()
        self.assertEqual(errcode, 0)
