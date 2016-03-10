from publisher import utils
from publisher.tests import base
from datetime import timedelta
from django.utils import timezone


class TestUtils(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_future_date(self):
        all_future_dates = [
            timedelta(seconds=1),
            timedelta(minutes=1),
            timedelta(days=1),
        ]
        for future_date in all_future_dates:
            self.assertTrue(utils.future_date(timezone.now() + future_date))

    def test_not_future_dates(self):
        all_past_dates = [
            timedelta(seconds=1),
            timedelta(minutes=1),
            timedelta(days=1),
        ]
        for past_date in all_past_dates:
            self.assertFalse(utils.future_date(timezone.now() - past_date))

    def test_dictmap_nofuncargs(self):
        test = {'a': 1, 'b': 2, 'c': 3}
        expected = {'a': 2, 'b': 3, 'c': 4}
        self.assertEqual(expected, utils.dictmap(lambda v: v+1, test))

    def test_dictmap_funcargs(self):
        test = {'a': 1, 'b': 2, 'c': 3}

        def func(v, increment=1):
            return v + increment

        expected = {'a': 3, 'b': 4, 'c': 5}
        self.assertEqual(expected, utils.dictmap(func, test, increment=2))
