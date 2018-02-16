from publisher import models
import logging
from django.db.models import Max, F, Q
from django.db.models import OuterRef, Subquery

LOG = logging.getLogger(__name__)

#
# PAW
#

def mkrow(av):
    pubdate = av.datetime_published
    update = None

    if av.status == models.VOR:
        # 'recent' report
        pubdate = av.min_vor
        update = av.datetime_published

    return {
        'title': av.title,
        'link': av.get_absolute_url(),
        'description': 'N/A',
        'author': {'name': 'N/A', 'email': 'N/A'},
        'category-list': [],
        'guid': av.get_absolute_url(),

        'pub-date': pubdate,
        'update-date': update,

        'obj': av
    }

# 'recent' report (VOR)

def paw_recent_report_raw_data(limit=None):
    "returns the SQL query used to generate the data for the 'recent' report"
    min_vor_subquery = models.ArticleVersion.objects \
        .filter(article=OuterRef('article')) \
        .filter(status='vor') \
        .values('datetime_published')[:1]

    query = models.ArticleVersion.objects \
        .select_related('article') \
        .defer('article_json_v1', 'article_json_v1_snippet') \
        .filter(status='vor') \
        .annotate(min_vor=Subquery(min_vor_subquery)) \
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
