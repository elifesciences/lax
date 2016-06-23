import itertools
from . import models, utils
from .utils import ymd
from functools import wraps
from django.db.models import Count
from itertools import islice
import logging

LOG = logging.getLogger(__name__)

def needs_peer_review(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        LOG.critical("this function has been explicitly flagged for peer review. it's author needs confirmation of it's correctness!")
        return func(*args, **kwargs)
    return wrapper

def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))

# 'published.csv'
def article_poa_vor_pubdates():
    def ymd_dt(av):
        if av and hasattr(av, 'datetime_published'):
            return ymd(av.datetime_published)
    def row(art):
        poa = art.earliest_poa()
        vor = art.earliest_vor()
        return (utils.doi2msid(art.doi), ymd_dt(poa), ymd_dt(vor))
    query = models.Article.objects.all() \
      .exclude(type__in=['article-commentary', 'editorial', 'book-review', 'discussion', 'correction']) \
      .exclude(volume=None) \
      .order_by('doi')
    return itertools.imap(row, query)


@needs_peer_review
def totals_for_year(year=2015):
    kwargs = {
        'version': 1,
        'datetime_published__year': year}
    rs = models.ArticleVersion.objects.filter(**kwargs)
    
    total = rs.count()
    total_poa = rs.filter(status='poa').count()
    total_vor = rs.filter(status='vor').count()

    assert total_poa + total_vor == total, "total poa + total vor don't add up to total published? wtf???"

    # totals for JATS 'type' (distinct from the EJP 'ejp-type'
    by_jats_type_count = rs.values('article__type').annotate(Count('article__type'))
    by_ejp_type_count = rs.values('article__type').annotate(Count('article__type'))

    def xcount(key):
        # ll: rs.values('article__type').annotate(Count('article__type'))    
        vals = rs.values(key).annotate(Count(key))
        def counts(row):
            count = row[key + '__count'] # 36
            article_type = row[key] # 'correction'
            return (article_type, count) # ll: (correction, 36)
        return map(counts, vals)
    
    jats_type_counts = xcount('article__type')
    ejp_type_counts = xcount('article__ejp_type')
    
    return {
        'description': 'totals for *articles* published',
        'params': {
            'year': year,
        },
        'results': {
            'total-published': total,
            'poa-published': total_poa,
            'vor-published': total_vor,
            'percent-poa': (total_poa / float(total)) * 100,
            'percent-vor': (total_vor / float(total)) * 100,
            'total-jats-types': jats_type_counts,
            'total-ejp-types': ejp_type_counts,
        }
    }

def version_totals_for_year(year=2015):
    kwargs = {
        'datetime_published__year': year
    }
    rs = models.ArticleVersion.objects.filter(**kwargs)

    total = rs.count()
    total_poa = rs.filter(status='poa').count()
    total_vor = rs.filter(status='vor').count()
    
    return {
        'title': 'article versions report',
        'description': 'totals for article *versions* published',
        'params': {
            'year': year,
        },
        'results': {
            'total-published': total,
            'total-poa-published': total_poa,
            'total-vor-published': total_vor,

            'percent-poa-published': (total_poa / float(total)) * 100,
            'percent-vor-published': (total_vor / float(total)) * 100,
        }
    }

def time_to_publication(year=2015):
    kwargs = {
        'articleversion__version': 1, # article is published
        # WARN: this should probably be date_accepted, but that isn't easily accessed yet
        'articleversion__datetime_published__year': year, # article was published in year. 
    }
    headers = ['doi', 'jats type', 'ejp type', 'date accepted', 'date poa published', 'date vor published', 'days to poa', 'days to vor', 'days to vor from poa']
    def row(art):
        accepted = art.date_accepted
        poa = getattr(art.earliest_poa(), 'datetime_published', None)
        vor = getattr(art.earliest_vor(), 'datetime_published', None)
        
        days_to_poa = None
        if poa and accepted:
            days_to_poa = (poa.date() - accepted).days

        days_to_vor = None
        if vor and accepted:
            days_to_vor = (vor.date() - accepted).days

        days_to_vor_from_poa = None
        if poa and vor:
            days_to_vor_from_poa = (vor - poa).days
            
        return [
            art.doi,
            art.type,
            art.ejp_type,
            art.date_accepted,
            utils.ymd(poa),
            utils.ymd(vor),

            days_to_poa,
            days_to_vor,
            days_to_vor_from_poa,
        ]
    return itertools.chain([headers], itertools.imap(row, models.Article.objects.filter(**kwargs)))
