from collections import OrderedDict
from publisher import models, fragment_logic
from publisher.utils import lmap
import logging
from django.db.models import Min, Max, F, Q

LOG = logging.getLogger(__name__)

'''
def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))
'''

#
#
#

def status_report():
    "useful insights into the current state of this lax instance"

    rs = models.ArticleVersion.objects \
        .select_related('article') \
        .defer('article_json_v1', 'article_json_v1_snippet') \
        .order_by('article__manuscript_id', 'version') \
        .all()

    def get_loc(av):
        try:
            obj = fragment_logic.get(av, models.XML2JSON)
            return obj.fragment['-meta']['location']
        except models.ArticleFragment.DoesNotExist:
            return 'no-article-fragment'
        except KeyError as err:
            return 'no-location-stored'

    def avi(av): # article-version-info
        return {
            'msid': av.article.manuscript_id,
            'version': av.version,
            'location': get_loc(av),
        }

    return OrderedDict([
        #'articles': {
        #    'total': al.count(),
        #    'total-published': ...
        #}
        ('article-versions', OrderedDict([
            ('total', rs.count()),
            ('total-published', rs.exclude(datetime_published=None).count()),
            ('invalid-unpublished', OrderedDict([
                ('desc', 'no article-json set, no datetime-published set',),
                ('total', rs.filter(article_json_v1=None, datetime_published=None).count()),
                ('list', lmap(avi, rs.filter(article_json_v1=None, datetime_published=None))),
            ])),
            ('invalid', OrderedDict([
                ('desc', 'no article-json set'),
                ('total', rs.filter(article_json_v1=None).count()),
                ('list', lmap(avi, rs.filter(article_json_v1=None))),
            ])),
            ('unpublished', OrderedDict([
                ('desc', 'no datetime-published set'),
                ('total', rs.filter(datetime_published=None).count()),
                ('list', lmap(avi, rs.filter(datetime_published=None))),
            ])),
        ]))
    ])

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
