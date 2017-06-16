from os.path import join
import copy
from publisher import utils, models, logic
from publisher.tests import base
import pytz
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

class TestUtils(base.BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ensure(self):
        self.assertRaises(utils.LaxAssertionError, utils.ensure, False, "msg")
        self.assertRaises(AssertionError, utils.ensure, False, "msg")
        self.assertRaises(AssertionError, utils.ensure, False, "%s")

    def test_dxdoi_link(self):
        cases = [
            ('eLife.09560', 'https://dx.doi.org/eLife.09560'),
        ]
        for given, expected in cases:
            self.assertEqual(utils.mk_dxdoi_link(given), expected)

    def test_json_dumps_rfc3339(self):
        dt = datetime(year=2001, month=1, day=1, hour=23, minute=59, second=59, microsecond=123, tzinfo=pytz.utc)
        struct = {'dt': dt}
        expected = '{"dt": "2001-01-01T23:59:59Z"}'
        self.assertEqual(utils.json_dumps(struct), expected)

    def test_json_dumps_rfc3339_on_non_utc(self):
        tz = pytz.timezone('Australia/Adelaide') # +9.5 hours ahead, but pytz thinks it's only +9
        dt = datetime(year=2001, month=1, day=1, hour=9, minute=59, second=59, microsecond=123, tzinfo=tz)
        struct = {'dt': dt}
        expected = '{"dt": "2001-01-01T00:59:59Z"}'
        self.assertEqual(utils.json_dumps(struct), expected)

    def test_resolve_paths(self):
        tests_dir = join(settings.SRC_DIR, 'publisher', 'tests', 'fixtures')
        cases = [
            (join(self.fixture_dir, 'ajson', 'elife.01968-invalid.json'), [
                join(tests_dir, 'ajson', 'elife.01968-invalid.json')
            ]),
            (join(self.fixture_dir, 'almost-empty-dir'), [
                join(tests_dir, 'almost-empty-dir', 'two.json'),
                join(tests_dir, 'almost-empty-dir', 'one.json'),
            ])
        ]
        for path, expected in cases:
            self.assertEqual(utils.resolve_path(path), expected)

    def test_resolve_paths_custom_ext(self):
        tests_dir = join(settings.SRC_DIR, 'publisher', 'tests', 'fixtures')
        cases = [
            (join(self.fixture_dir, 'almost-empty-dir'), [
                join(tests_dir, 'almost-empty-dir', 'two.empty'),
                join(tests_dir, 'almost-empty-dir', 'one.empty'),
            ])
        ]
        for path, expected in cases:
            self.assertEqual(utils.resolve_path(path, ext='.empty'), expected)

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
            self.assertFalse(utils.isint(not_int), 'testing %s' % not_int)

    def test_nth(self):
        expected_list = [
            ('abc', 0, 'a'),
            ('abc', 1, 'b'),
            ('abc', 2, 'c'),
            ('abc', 3, None),
            ('abc', -1, 'c'),
            ('abc', -3, 'a'),
            ('abc', -4, None),

            ([1, 2, 3], 0, 1),
            ([], 0, None),
            ((1, 2, 3), 0, 1),

            (None, 0, None),
            (None, -1, None),
            (None, 1, None),
        ]
        for val, idx, expected in expected_list:
            self.assertEqual(utils.nth(idx, val), expected, 'testing %s %s %s' % (val, idx, expected))

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
            (utils.first, [1, 2, 3], 1),
            (utils.first, (1, 2, 3), 1),
            (utils.first, 'abc', 'a'),
            (utils.second, [1, 2, 3], 2),
            (utils.second, (1, 2, 3), 2),
            (utils.second, 'abc', 'b'),
        ]
        for fn, val, expected in expected_list:
            self.assertEqual(fn(val), expected)

    def test_delall(self):
        x = {'a': 1, 'b': 2, 'c': 3}
        expected_list = [
            (['a', 'b', 'c'], {}),
            (['a', 'b'], {'c': 3}),
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
        self.assertEqual(expected, utils.dictmap(lambda v: v + 1, test))

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
            self.assertEqual(utils.has_all_keys(case, args), expected, "%s %s %s" % (case, args, expected))

    def test_utcnow(self):
        "utcnow returns a UTC datetime"
        # TODO: this test could be improved
        now = utils.utcnow()
        self.assertEqual(now.tzinfo, pytz.utc)

    def test_todt(self):
        cases = [
            # naive dtstr becomes utc
            ("2001-01-01", \
             datetime(year=2001, month=1, day=1, tzinfo=pytz.utc)),

            # aware but non-utc become utc
            ("2001-01-01T23:30:30+09:30", \
             datetime(year=2001, month=1, day=1, hour=14, minute=0, second=30, tzinfo=pytz.utc)),
        ]
        for string, expected in cases:
            self.assertEqual(utils.todt(string), expected)

    def test_deepmerge(self):
        cases = [
            ({'a': 'a'}, {'a': 'b'}, {'a': 'b'}),
            ({'a': 'a'}, {'b': 'b', 'c': 'c'}, {'a': 'a', 'b': 'b', 'c': 'c'})
        ]
        for row in cases:
            dict_list, expected = row[:-1], row[-1]
            self.assertEqual(utils.merge_all(dict_list), expected)
