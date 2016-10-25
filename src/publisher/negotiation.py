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
    ('ArticleList', 'application/vnd.elife.articles-list+json', [1]),
    ('POAArticle', 'application/vnd.elife.article-poa+json', [1]),
    ('VORArticle', 'application/vnd.elife.article-vor+json', [1]),
    ('ArticleHistory', 'application/vnd.elife.article-history+json', [1])
]

map(mktype, _dynamic_types)
