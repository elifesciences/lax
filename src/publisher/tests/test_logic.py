from base import BaseCase
from publisher import logic


class TestLogic(BaseCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_dxdoi_link(self):
        cases = [
            ('eLife.09560', 'http://dx.doi.org/eLife.09560'),
        ]
        for given, expected in cases:
            self.assertEqual(logic.mk_dxdoi_link(given), expected)
