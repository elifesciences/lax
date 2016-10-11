import os
from django.test import TestCase
from publisher import models

class BaseCase(TestCase):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    fixture_dir = os.path.join(this_dir, 'fixtures')

    def freshen(self, obj):
        return type(obj).objects.get(pk=obj.pk)

    def unpublish(self, msid, version):
        "'unpublishes' an article"
        av = models.ArticleVersion.objects.get(article__manuscript_id=msid, version=version)
        av.datetime_published = None
        av.save()
        return av
