import itertools
from . import models, utils
from .utils import ymd

from itertools import islice

def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))

def article_poa_vor_pubdates():
    def ymd_dt(av):
        if av and hasattr(av, 'datetime_published'):
            return ymd(av.datetime_published)
    def row(art):
        poa = art.earliest_poa()
        vor = art.earliest_vor()
        return (utils.doi2msid(art.doi), ymd_dt(poa), ymd_dt(vor))
    query = models.Article.objects.all().order_by('doi')
    return itertools.imap(row, query)
