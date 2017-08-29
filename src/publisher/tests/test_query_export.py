import re
from explorer import models
from django.core.management import call_command
from .base import BaseCase
from io import StringIO

class CLI(BaseCase):
    def setUp(self):
        self.nom = 'query_export'
        q = models.Query(**{
            'title': 'dummy-query',
            'sql': 'select count(*) from publisher_article;'
        })
        q.save()
        self.q = models.Query.objects.first()

    def call_command(self, *args, **kwargs):
        stdout = StringIO()
        try:
            kwargs['stdout'] = stdout
            call_command(*args, **kwargs)
        except SystemExit as err:
            return err.code, stdout
        self.fail("management command should always throw a systemexit()")

    def test_export_all_from_cli(self):
        args = [self.nom, '--skip-upload']
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)

    def test_export_specific_from_cli(self):
        args = [self.nom, '--skip-upload', '--query-id', str(self.q.id)]
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)
        cregex = re.compile('query.--dummy-query.csv')
        self.assertNotEqual(cregex.match(stdout.getvalue()), None)

    def test_export_empty_queryset(self):
        "no queries? no worries."
        args = [self.nom, '--skip-upload']
        models.Query.objects.all().delete()
        errcode, stdout = self.call_command(*args)
        self.assertEqual(errcode, 0)
