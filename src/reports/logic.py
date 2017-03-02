from collections import OrderedDict
import itertools
from publisher import utils, models
from publisher.utils import ymd, lmap
from django.db.models import Count
from itertools import islice
import logging
from django.db.models import Min, Max, F, Q

LOG = logging.getLogger(__name__)

def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))

#
#
#

def status_report():
    "useful insights into the current state of this lax instance"

    #al = models.Article.objects.all()
    avl = models.ArticleVersion.objects \
        .select_related('article') \
        .defer('article_json_v1', 'article_json_v1_snippet') \
        .order_by('article__manuscript_id', 'version') \
        .all()

    def get_loc(av):
        try:
            return av.article.articlefragment_set.get(type=models.XML2JSON).fragment['article']['-meta']['location']
        except models.ArticleFragment.DoesNotExist:
            return 'no-article-fragment'
        except KeyError:
            return 'no-location-stored'

    def avi(av):
        return {
            'msid': av.article.manuscript_id,
            'version': av.version,
        }

    def avil(av):
        d = avi(av)
        d.update({
            'location': get_loc(av),
        })
        return d

    return OrderedDict([
        #'articles': {
        #    'total': al.count(),
        #    'total-published': ...
        #}
        ('article-versions', OrderedDict([
            ('total', avl.count()),
            ('total-published', avl.exclude(datetime_published=None).count()),
            ('invalid-unpublished', OrderedDict([
                ('desc', 'no article-json set, no datetime-published set',),
                ('total', avl.filter(article_json_v1=None, datetime_published=None).count()),
                ('list', lmap(avil, avl.filter(article_json_v1=None, datetime_published=None))),
            ])),
            ('invalid', OrderedDict([
                ('desc', 'no article-json set'),
                ('total', avl.filter(article_json_v1=None).count()),
                ('list', lmap(avil, avl.filter(article_json_v1=None))),
            ])),
            ('unpublished', OrderedDict([
                ('desc', 'no datetime-published set'),
                ('total', avl.filter(datetime_published=None).count()),
                ('list', lmap(avi, avl.filter(datetime_published=None))),
            ])),
        ]))
    ])


# 'published.csv'
def article_poa_vor_pubdates():
    def ymd_dt(av):
        if av and hasattr(av, 'datetime_published'):
            return ymd(av.datetime_published)

    def row(art):
        poa = art.earliest_poa()
        vor = art.earliest_vor()
        return (art.manuscript_id, ymd_dt(poa), ymd_dt(vor))
    query = models.Article.objects.all() \
        .exclude(type__in=['article-commentary', 'editorial', 'book-review', 'discussion', 'correction']) \
        .exclude(volume=None) \
        .order_by('manuscript_id')
    return map(row, query)


#
# PAW
#

def dt(av):
    if av and hasattr(av, 'datetime_published'):
        return av.datetime_published

def mkrow(av):
    return {
        'title': av.title,
        'link': av.get_absolute_url(),
        'description': 'N/A',
        'author': {'name': 'N/A', 'email': 'N/A'},
        'category-list': [],
        'guid': av.get_absolute_url(),
        'pub-date': dt(av),

        'obj': av
    }

# 'recent' report (VOR)

def paw_recent_report_raw_data(limit=None):
    "returns the SQL query used to generate the data for the 'recent' report"
    query = models.ArticleVersion.objects \
        .select_related('article') \
        .defer('article_json_v1', 'article_json_v1_snippet') \
        .annotate(min_vor=Min('article__articleversion__version')) \
        .filter(article__articleversion__version=F('min_vor')) \
        .filter(status='vor') \
        .order_by('-datetime_published')

    if limit:
        assert isinstance(limit, Q), "the report can only be limited with a django 'Q' object"
        # may want to .exclude at some point, until then, .filter
        query = query.filter(limit)

    return query

def paw_recent_data(limit=None):
    "turns the raw SQL results data into rows suitable for a report"
    return map(mkrow, paw_recent_report_raw_data(limit))


# 'ahead' report (POA)

def paw_ahead_report_raw_data(limit=None):
    # only select max version ArticleVersions where the Article has no POA versions
    query = models.ArticleVersion.objects \
        .select_related('article') \
        .defer('article_json_v1', 'article_json_v1_snippet') \
        .annotate(max_version=Max('article__articleversion__version')) \
        .filter(version=F('max_version')) \
        .exclude(status='vor') \
        .order_by('-datetime_published')

    if limit:
        assert isinstance(limit, Q), "the report can only be limited with a django 'Q' object"
        # may want to .exclude at some point, until then, .filter
        query = query.filter(limit)

    return query

def paw_ahead_data(limit=None):
    "'ahead' data is POA only"
    return map(mkrow, paw_ahead_report_raw_data(limit))

def totals_for_year(year=2015):
    kwargs = {
        'version': 1,
        'datetime_published__year': year}
    rs = models.ArticleVersion.objects \
        .defer('article_json_v1', 'article_json_v1_snippet') \
        .filter(**kwargs)

    total = rs.count()
    total_poa = rs.filter(status='poa').count()
    total_vor = rs.filter(status='vor').count()

    assert total_poa + total_vor == total, "total poa + total vor don't add up to total published? wtf???"

    # totals for JATS 'type' (distinct from the EJP 'ejp-type'
    #by_jats_type_count = rs.values('article__type').annotate(Count('article__type'))
    #by_ejp_type_count = rs.values('article__type').annotate(Count('article__type'))

    def xcount(key):
        # ll: rs.values('article__type').annotate(Count('article__type'))
        vals = rs.values(key).annotate(Count(key))

        def counts(row):
            count = row[key + '__count'] # 36
            article_type = row[key] # 'correction'
            return (article_type, count) # ll: (correction, 36)
        return lmap(counts, vals)

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
    rs = models.ArticleVersion.objects \
        .defer('article_json_v1', 'article_json_v1_snippet') \
        .filter(**kwargs)

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
    return itertools.chain([headers], map(row, models.Article.objects.filter(**kwargs)))

'''
# once off
from datetime import datetime
from publisher.models import AF
def arb1():
    nov_2015 = datetime(year=2015, month=11, day=1)

    accepted = [
        Q(initial_decision=AF),
        Q(decision=AF),
        Q(rev1_decision=AF),
        Q(rev2_decision=AF),
        Q(rev3_decision=AF),
        Q(rev4_decision=AF),
    ]
    aq = reduce(lambda q1,q2: q1 | q2, accepted)

    al = models.Article.objects \
      .filter(date_initial_decision__gte=nov_2015) \
      .filter(ejp_type='RA') \
      .filter(aq)

    import json
    from os.path import join
    from django.conf import settings
    has_digest_results = json.load(open(join(settings.PROJECT_DIR, 'has_digest.json'), 'r'))
    from collections import OrderedDict
    def mkrow(art):
        vor = art.earliest_vor()
        key = "%05d" % art.manuscript_id
        digest = has_digest_results.get(key, "UNKNOWN (no xml)")
        return OrderedDict([
            ('id', art.manuscript_id),
            ('date-accepted', art.date_accepted.isoformat()),
            ('first-vor', vor.datetime_published.isoformat() if vor else None,),
            ('has-digest?', digest['digest?'] if isinstance(digest, dict) else digest),
        ])

    results = filter(lambda row: row['first-vor'], map(mkrow, al))

    import csv
    keys = results[0].keys()
    with open(join(settings.PROJECT_DIR, 'has_digest.csv'), 'w') as fh:
        dict_writer = csv.DictWriter(fh, keys)
        dict_writer.writeheader()
        dict_writer.writerows(results)
'''
