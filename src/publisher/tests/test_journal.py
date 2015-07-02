from base import BaseCase
from publisher import logic, models
from django.conf import settings

class Journal(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_fetch_journal(self):
        self.assertEqual(0, models.Journal.objects.count())
        j = logic.journal()
        self.assertEqual(1, models.Journal.objects.count())
        self.assertEqual(j.name, settings.PRIMARY_JOURNAL)
