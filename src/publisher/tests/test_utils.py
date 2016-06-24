import copy
from publisher import utils, models, logic
from publisher.tests import base
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

class TestUtils(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_isint(self):
        int_list = [
            1,
            -1,
            '-1',
            '1',
            '1111111111',
            '99999999999999999999999999999999999',
            0xDEADBEEF, # hex
        ]
        for int_val in int_list:
            self.assertTrue(utils.isint(int_val))

    def test_isnotint(self):
        not_int_list = ['one', 'a', utils]
        for not_int in not_int_list:
            print 'testing',not_int
            self.assertFalse(utils.isint(not_int))

    def test_nth(self):
        expected_list = [
            ('abc', 0, 'a'),
            ('abc', 1, 'b'),
            ('abc', 2, 'c'),
            ('abc', 3, None),
            ('abc', -1, 'c'),
            ('abc', -3, 'a'),
            ('abc', -4, None),

            ([1,2,3], 0, 1),
            ([], 0, None),
            ((1,2,3), 0, 1),

            (None, 0, None),
            (None, -1, None),
            (None, 1, None),
        ]
        for val, idx, expected in expected_list:
            print 'testing',val,idx,expected
            self.assertEqual(utils.nth(idx, val), expected)

    def test_bad_nths(self):
        bad_list = [
            ({}, 0),
            ({'a': 1}, 0),
            #(None, 0), # attempting to access something in a None now gives you None
        ]
        for val, idx in bad_list:
            self.assertRaises(TypeError, utils.nth, idx, val)

    def test_first_second(self):
        expected_list = [
            (utils.first, [1,2,3], 1),
            (utils.first, (1,2,3), 1),
            (utils.first, 'abc', 'a'),
            (utils.second, [1,2,3], 2),
            (utils.second, (1,2,3), 2),
            (utils.second, 'abc', 'b'),
        ]
        for fn, val, expected in expected_list:
            self.assertEqual(fn(val), expected)

    def test_delall(self):
        x = {'a': 1, 'b': 2, 'c': 3}
        expected_list = [
            (['a','b','c'], {}),
            (['a','b'], {'c': 3}),
            (['a'], {'b': 2, 'c': 3}),
            ([], x),
        ]
        for keys, expected in expected_list:
            y = copy.deepcopy(x)
            utils.delall(y, keys)
            self.assertEqual(y, expected)

    def test_delall_bad_idx(self):
        x = {'a': 1, 'b': 2, 'c': 3}
        y = copy.deepcopy(x)
        utils.delall(x, ['foo', 'bar', 'baz'])
        self.assertEqual(x, y)
            
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

    def test_todict(self):
        self.assertEqual(models.Journal.objects.count(), 0)
        jnl = logic.journal()
        jnl_data = utils.to_dict(jnl)
        self.assertTrue(isinstance(jnl_data, dict))
        self.assertEqual(jnl_data['name'], settings.PRIMARY_JOURNAL['name'])

    def test_has_all_keys(self):
        data = {'a': 1, 'b': 2}
        cases = [
            (data, ['a'], True),
            (data, ['a', 'b'], True),
            (data, ['a', 'b', 'c'], False),
            (data, [0], False),
            (data, [0, 1], False),
            (data, [self], False),
        ]
        for case, args, expected in cases:
            try:
                self.assertEqual(utils.has_all_keys(case, args), expected)
            except AssertionError:
                print case,args,expected
                raise
        
