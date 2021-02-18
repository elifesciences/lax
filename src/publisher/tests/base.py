# from mock import patch
from io import StringIO
import os, json  # , copy
from django.test import TestCase as DjangoTestCase, TransactionTestCase
from publisher import models, utils, ajson_ingestor
from django.core.management import call_command as dj_call_command
import unittest

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = os.path.join(THIS_DIR, "fixtures")


class SimpleBaseCase(unittest.TestCase):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    fixture_dir = os.path.join(this_dir, "fixtures")
    maxDiff = None

    # NOTE: relationship creation can also be disabled with:
    # @override_settings(ENABLE_RELATIONS=False)
    def load_ajson(self, path, strip_relations=True):
        "loads an article-json fixture. conveniently strips relations by default"
        data = json.load(open(path, "r"))
        if strip_relations:
            # remove these values here so they don't interfere in creation
            utils.delall(
                data["article"],
                ["-related-articles-internal", "-related-articles-external"],
            )
        return data

    def load_ajson2(self, path_or_data):
        "loads an article-json fixture. conveniently strips relations and other troublesome things"
        if isinstance(path_or_data, str):
            # assume string is a path to a file
            path = path_or_data
            data = json.load(open(path, "r"))
        else:
            # assume data is article-json
            data = path_or_data

        # remove the 'journal' and 'snippet' sections if present
        if "article" in data:
            data = data["article"]

        # remove these values here so they don't interfere in creation
        utils.delall(
            data,
            ["-related-articles-internal", "-related-articles-external", "-history"],
        )

        # remove these values here so they don't interfere with comparison
        utils.delall(data, ["-meta", "statusDate", "versionDate"])

        return data

    def publish_ajson(self, path):
        return ajson_ingestor.ingest_publish(self.load_ajson(path))

    def freshen(self, obj):
        return utils.freshen(obj)

    def unpublish(self, msid, version=None):
        "'unpublishes' an article"
        if not version:
            # unpublish *all* versions of an article
            for av in models.Article.objects.get(
                manuscript_id=msid
            ).articleversion_set.all():
                av.datetime_published = None
                av.save()
        else:
            av = models.ArticleVersion.objects.get(
                article__manuscript_id=msid, version=version
            )
            av.datetime_published = None
            av.save()

    def call_command(self, *args, **kwargs):
        stdout = StringIO()
        try:
            kwargs["stdout"] = stdout
            dj_call_command(*args, **kwargs)
        except SystemExit as err:
            return err.code, stdout.getvalue()
        self.fail("ingest script should always throw a systemexit()")

    def assertJSONEqual(self, x, y, *args):
        self.assertEqual(json.dumps(x, indent=2), json.dumps(y, indent=2), *args)


#
#
#


class BaseCase(SimpleBaseCase, DjangoTestCase):
    pass


class TransactionBaseCase(SimpleBaseCase, TransactionTestCase):
    pass
