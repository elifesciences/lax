from io import StringIO
import os, json
from django.test import TestCase
from publisher import models, utils
from django.core.management import call_command

class BaseCase(TestCase):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    fixture_dir = os.path.join(this_dir, 'fixtures')
    maxDiff = None

    # eh - not sure about this. can I patch entire classes
    # to turn auto-stubbing off??
    def load_ajson(self, path, strip_relations=True):
        "loads an article-json fixture. conveniently strips relations by default"
        data = json.load(open(path, 'r'))
        if strip_relations:
            # remove these values here so they don't interfere in creation
            utils.delall(data['article'], ['-related-articles-internal', '-related-articles-external'])
        return data

    def freshen(self, obj):
        return utils.freshen(obj)

    def unpublish(self, msid, version=None):
        "'unpublishes' an article"
        if not version:
            # unpublish *all* versions of an article
            for av in models.Article.objects.get(manuscript_id=msid).articleversion_set.all():
                av.datetime_published = None
                av.save()
        else:
            av = models.ArticleVersion.objects.get(article__manuscript_id=msid, version=version)
            av.datetime_published = None
            av.save()

    def call_command(self, *args, **kwargs):
        stdout = StringIO()
        try:
            kwargs['stdout'] = stdout
            call_command(*args, **kwargs)
        except SystemExit as err:
            return err.code, stdout.getvalue()
        self.fail("ingest script should always throw a systemexit()")
