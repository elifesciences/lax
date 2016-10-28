import os
from django.test import TestCase
from publisher import models

class BaseCase(TestCase):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    fixture_dir = os.path.join(this_dir, 'fixtures')
    maxDiff = None

    def freshen(self, obj):
        return type(obj).objects.get(pk=obj.pk)

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
        #return av
