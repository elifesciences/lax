from django.db import connection
from . import models
from django.conf import settings
import logging
from publisher import eif_ingestor, utils, relation_logic
from publisher.utils import ensure, lmap, lfilter, firstnn, second, exsubdict
from django.utils import timezone
from django.db.models import ObjectDoesNotExist, Max, F  # , Q, When

LOG = logging.getLogger(__name__)

def journal(name=None):
    journal = {'name': name}
    if not name:
        journal = settings.PRIMARY_JOURNAL
    if 'inception' in journal:
        inception = journal['inception']
        if timezone.is_naive(journal['inception']):
            inception = timezone.make_aware(journal['inception'])
        journal['inception'] = inception
    obj, new = models.Journal.objects.get_or_create(**journal)
    if new:
        LOG.info("created new Journal %s", obj)
    return obj

def article(doi, version=None):
    """returns the latest version of the article identified by the
    doi, or the specific version given.
    Raises DoesNotExist if article not found."""
    try:
        article = models.Article.objects.get(doi__iexact=doi)
        if version:
            return article, article.articleversion_set.exclude(datetime_published=None).get(version=version)
        return article, article.articleversion_set.exclude(datetime_published=None).latest('version')
    except ObjectDoesNotExist:
        raise models.Article.DoesNotExist()

def article_versions(doi):
    "returns all versions of the given article"
    return models.ArticleVersion.objects.filter(article__doi__iexact=doi).exclude(datetime_published=None)


# TODO: move this into `tests/`
def add_or_update_article(**article_data):
    """TESTING ONLY. given article data it attempts to find the
    article and update it, otherwise it will create it, filling
    any missing keys with dummy data. returns the created article."""
    assert 'doi' in article_data or 'manuscript_id' in article_data, \
        "a value for 'doi' or 'manuscript_id' *must* exist"

    if 'manuscript_id' in article_data:
        article_data['doi'] = utils.msid2doi(article_data['manuscript_id'])
    elif 'doi' in article_data:
        article_data['manuscript_id'] = utils.doi2msid(article_data['doi'])

    filler = [
        'title',
        'doi',
        'manuscript_id',
        ('volume', 1),
        'path',
        'article-type',
        ('ejp_type', 'RA'),
        ('version', 1),
        ('pub-date', '2012-01-01'),
        ('status', 'vor'),
    ]
    article_data = utils.filldict(article_data, filler, 'pants-party')
    return eif_ingestor.import_article(journal(), article_data, create=True, update=True)

#
#
#

def placeholder(av):
    return {
        '-invalid': True,
        'id': av.article.manuscript_id,
        'published': av.article.datetime_published,
        'versionDate': av.datetime_published,
        'version': av.version,
        'status': av.status
    }

def article_json(av):
    "returns the *valid* article json for the given article version."
    return av.article_json_v1 or None

def article_snippet_json(av, placeholder_if_invalid=True):
    "return the *valid* article snippet json for the given article version"
    return av.article_json_v1_snippet or placeholder(av) if placeholder_if_invalid else None

#
# latest article versions
#

def validate_pagination_params(page, per_page, order):
    order = str(order).strip().upper()
    ensure(str(order).upper() in ['ASC', 'DESC'], "unknown ordering %r" % order)

    ensure(all(map(utils.isint, [page, per_page])), "'page' and 'per-page' must be integers")

    return page, per_page, order

def latest_published_article_versions(page=1, per_page=-1, order='DESC'):
    limit = per_page
    offset = per_page * (page - 1)

    sql = """
    SELECT
       pav.id, pav.article_id, pav.title, pav.version, pav.status, pav.datetime_published,
       pav.datetime_record_created, pav.datetime_record_updated

    FROM publisher_articleversion pav,

      (SELECT pav2.article_id,
              max(version) AS max_ver
       FROM publisher_articleversion pav2
       WHERE datetime_published IS NOT NULL
       GROUP BY pav2.article_id) as pav2,
       publisher_article pa

    WHERE
       pav.article_id = pav2.article_id AND pav.version = pav2.max_ver
       AND pav.article_id = pa.id

    ORDER BY datetime_published %s, pa.manuscript_id %s""" % (order, order)

    with connection.cursor() as cursor:
        total_sql = "select COUNT(*) from (%s) as subq" % sql
        cursor.execute(total_sql)
        total = cursor.fetchone()[0]

    if per_page > 0:
        sql += """

    LIMIT %s

    OFFSET %s""" % (limit, offset)

    q = models.ArticleVersion.objects.raw(sql)

    return total, list(q)

def latest_unpublished_article_versions(page=1, per_page=-1, order='DESC'):
    start = (page - 1) * per_page
    end = start + per_page
    order_by = ['datetime_published', 'article__manuscript_id']
    if order == 'DESC':
        order_by = ['-' + o for o in order_by]

    q = models.ArticleVersion.objects \
        .select_related('article') \
        .annotate(max_version=Max('article__articleversion__version')) \
        .filter(version=F('max_version')) \
        .order_by(*order_by)

    total = q.count()

    if per_page > 0:
        q = q[start:end]

    return total, list(q)

def latest_article_version_list(page=1, per_page=-1, order='DESC', only_published=True):
    "returns a list of the most recent article versions for all articles."
    args = validate_pagination_params(page, per_page, order)
    if only_published:
        return latest_published_article_versions(*args)
    return latest_unpublished_article_versions(*args)

def most_recent_article_version(msid, only_published=True):
    "returns the most recent ArticleVersion for the given manuscript id"
    try:
        latest = models.ArticleVersion.objects \
            .select_related('article') \
            .filter(article__manuscript_id=msid) \
            .order_by('-version')

        if only_published:
            latest = latest.exclude(datetime_published=None)

        return latest[0]
    except IndexError:
        raise models.Article.DoesNotExist()

def article_version(msid, version, only_published=True):
    "returns the specified article version for the given article id"
    try:
        qs = models.ArticleVersion.objects \
            .select_related('article') \
            .filter(version=version) \
            .filter(article__manuscript_id=msid)
        if only_published:
            qs = qs.exclude(datetime_published=None)
        return qs[0]
    except IndexError:
        # raise an AV DNE because they asked for a version specifically
        raise models.ArticleVersion.DoesNotExist()

def article_version_list(msid, only_published=True):
    "returns a list of article versions for the given article id"
    qs = models.ArticleVersion.objects \
        .select_related('article') \
        .filter(article__manuscript_id=msid) \
        .order_by('version')
    if only_published:
        qs = qs.exclude(datetime_published=None)
    if not qs.count():
        raise models.Article.DoesNotExist()
    return qs

def relationships(msid, only_published=True):
    "returns all relationships for the given article"
    av = most_recent_article_version(msid, only_published)

    extr = relation_logic.external_relationships_for_article_version(av)
    intr = relation_logic.internal_relationships_for_article_version(av)

    # the internal relationships must be snippets of the latest version of that article
    def relation_snippet(art):
        try:
            return article_snippet_json(most_recent_article_version(art.manuscript_id, only_published))
        except models.Article.DoesNotExist:
            # reference to an article that could not be found!
            # it is either:
            # * a stub (hasn't finished production) or
            # * unpublished (finished production but unpublished)
            # neither are error conditions
            pass
    avl = lfilter(None, lmap(relation_snippet, intr))

    # pull the citation from each external relation
    extcl = [aver.citation for aver in extr]

    return extcl + avl

#
#
#

def date_received(art):
    # the date received, scraped from the xml, is guaranteed to not exist for certain article types
    # the initial quality check date will not exist under certain circumstances:
    # James, 20170317: "there are some instances in the archive where articles were essentially first submitted as full submissions rather than initial submissions, due to appeals or previous interactions etc. The logic we've been using for PoA is that if there is no initial qc date, use the full qc date."
    return firstnn([art.date_received, art.date_initial_qc, art.date_full_qc])

def date_accepted(art):
    attrs = [
        # scraped from the xml, guaranteed to not exist for certain article types
        (models.AF, art.date_accepted),

        # use ejp values if not above
        (art.initial_decision, art.date_initial_decision),
        (art.decision, art.date_full_decision),
        (art.rev1_decision, art.date_rev1_decision),
        (art.rev2_decision, art.date_rev2_decision),
        (art.rev3_decision, art.date_rev3_decision),
        (art.rev4_decision, art.date_rev4_decision)]
    return second(firstnn([pair for pair in attrs if pair[0] == models.AF]))

EXCLUDE_RECEIVED_ACCEPTED_DATES = [models.EDITORIAL, models.INSIGHT]

def article_version_history(msid, only_published=True):
    "returns a list of snippets for the history of the given article"
    article = models.Article.objects.get(manuscript_id=msid)
    avl = article.articleversion_set.all()
    if only_published:
        avl = avl.exclude(datetime_published=None)

    if not avl.count():
        # no article versions available, fail
        raise models.Article.DoesNotExist()

    struct = {
        'received': date_received(article),
        'accepted': date_accepted(article),
        'versions': lmap(article_snippet_json, avl)
    }

    if article.type in EXCLUDE_RECEIVED_ACCEPTED_DATES:
        struct = exsubdict(struct, ['received', 'accepted'])

    return struct

def bulk_article_version_history(only_published=True):
    for art in models.Article.objects.all():
        result = article_version_history(art.manuscript_id, only_published)
        result['msid'] = art.manuscript_id
        yield result
