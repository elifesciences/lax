from django.conf import settings
from publisher.tests import base
from datetime import datetime, timedelta
from publisher import logic, models
from django.utils import timezone
from django.utils.timezone import make_aware as aware
from django.test import Client
from django.core.urlresolvers import reverse

class TestCorrections(base.BaseCase):
    def setUp(self):
        self.journal = logic.journal()

    def tearDown(self):
        pass

    def test_correction_model(self):
        "a correction object can be created against an article"
        art = {'title': 'baz',
               'version': 1,
               'doi': "10.7554/eLife.DUMMY",
               'journal': self.journal}
        artobj = logic.add_or_update_article(**art)
        correction = models.ArticleCorrection(**{
            'article': artobj,
            'datetime_corrected': datetime.now()})
        correction.save()
        self.assertEqual(1, models.Article.objects.count())
        self.assertEqual(1, models.ArticleCorrection.objects.count())
        self.assertEqual(artobj.id, correction.article.id)


class TestCorrectionsLogic(base.BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        art = {'title': 'baz',
               'version': 1,
               'doi': "10.7554/eLife.DUMMY",
               'journal': self.journal}
        self.art = logic.add_or_update_article(**art)

    def tearDown(self):
        pass

    def test_create_correction(self):
        "a correction can be created"
        self.assertEqual(0, models.ArticleCorrection.objects.count())
        logic.record_correction(self.art)
        self.assertEqual(1, models.ArticleCorrection.objects.count())

    def test_create_correction_specific_date(self):
        "a correction can be created for an article for a specific date in time"
        self.assertEqual(0, models.ArticleCorrection.objects.count())
        when = aware(datetime(year=2016, month=02, day=29))
        logic.record_correction(self.art, when)
        self.assertEqual(1, models.ArticleCorrection.objects.count())
        clean_correction = models.ArticleCorrection.objects.all()[0]
        self.assertEqual(when, clean_correction.datetime_corrected)

    def test_create_correction_future_date(self):
        "a correction can't have a date in the future"
        when = timezone.now() + timedelta(days=1)
        self.assertRaises(AssertionError, logic.record_correction, self.art, when)

    def test_create_correction_way_in_the_past(self):
        "a correction can't have a date before it's journal existed"
        when = self.journal.inception - timedelta(days=1)
        self.assertRaises(AssertionError, logic.record_correction, self.art, when)

class TestCorrectionsAPI(base.BaseCase):
    def setUp(self):
        self.journal = logic.journal()
        art = {'title': 'baz',
               'version': 1,
               'doi': "10.7554/eLife.DUMMY",
               'journal': self.journal}
        self.art = logic.add_or_update_article(**art)
        self.c = Client()

    def tearDown(self):
        pass

    def test_record_correction(self):
        "a correction can be made via the api"
        self.assertEqual(0, models.ArticleCorrection.objects.count())
        resp = self.c.post(reverse('api-record-article-correction', kwargs={'doi': self.art.doi,
                                                                    'version': self.art.version}))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(1, models.ArticleCorrection.objects.count())
    '''
    def test_record_elaborate_correction(self):
        "a correction with a custom date and a description can be made via the api"
        self.assertEqual(0, models.ArticleCorrection.objects.count())
        params = {'doi': self.art.doi, 'version': self.art.version}
        url = reverse('api-record-article-correction', kwargs=params)
        corrected = (timezone.now() - timedelta(days=1))
        payload = {
            'description': 'test description',
            'datetime_corrected': corrected.isoformat(),
        }
        resp = self.c.post(url, payload, content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(1, models.ArticleCorrection.objects.count())
        correction = models.ArticleCorrection.objects.all()[0]
        self.assertEqual(correction.datetime_corrected, corrected)
        self.assertEqual(correction.description, payload['description'])
    '''
