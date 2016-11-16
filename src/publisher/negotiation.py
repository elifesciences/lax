"""Adds a list of supported media types to Django REST so it
doesn't spaz out when you ask for a custom media article in the
Accept header."""

from rest_framework.renderers import JSONRenderer

def mktype(row):
    nom, mime, version_list = row
    klass_list = map(lambda ver: ("%sVersion%s" % (nom, ver), "%s; version=1" % mime), version_list)
    global_scope = globals()

    def gen_klass(klass_row):
        nom, mime = klass_row
        global_scope[nom] = type(nom, (JSONRenderer,), {'media_type': mime})
    map(gen_klass, klass_list)

_dynamic_types = [
    # class name, media type, known version list
    ('ArticleList', 'application/vnd.elife.article-list+json', [1]),
    ('POAArticle', 'application/vnd.elife.article-poa+json', [1]),
    ('VORArticle', 'application/vnd.elife.article-vor+json', [1]),
    ('ArticleHistory', 'application/vnd.elife.article-history+json', [1])
]

map(mktype, _dynamic_types)
