import json
from django.db import connection, reset_queries
from . import models
from django.conf import settings
import logging
from publisher import utils, relation_logic
from publisher.utils import ensure, lmap, lfilter, firstnn, second, exsubdict
from django.utils import timezone
from django.db.models import Max, F  # , Q, When
from psycopg2.extensions import AsIs

LOG = logging.getLogger(__name__)


def qdebug(f):
    "query debug output. prints number of sql queries and time taken in ms"

    def wrap(*args, **kwargs):
        reset_queries()
        result = f(*args, **kwargs)
        qt = [(float(query["time"]) * 1000) for query in connection.queries]

        print("%s queries" % len(qt))
        print("%s s" % sum(qt))
        print()

        return result

    return wrap


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def execute_sql(filename, params):
    with connection.cursor() as cursor:
        cursor.execute(settings.SQL_MAP[filename], params)
        return dictfetchall(cursor)


#
#
#


def journal(name=None):
    journal = {"name": name}
    if not name:
        journal = settings.PRIMARY_JOURNAL
    if "inception" in journal:
        inception = journal["inception"]
        if timezone.is_naive(journal["inception"]):
            inception = timezone.make_aware(journal["inception"])
        journal["inception"] = inception
    obj, new = models.Journal.objects.get_or_create(**journal)
    if new:
        LOG.info("created new Journal %s", obj)
    return obj


#
#
#


def placeholder(av):
    "returns a snippet 'stub' for when an ArticleVersion object isn't valid"
    return {
        "-invalid": True,
        "id": av.article.manuscript_id,
        "published": av.article.datetime_published,
        "versionDate": av.datetime_published,
        "version": av.version,
        "status": av.status,
    }


def article_json(av):
    "returns the *valid* article json for the given article version or None if invalid."
    return av.article_json_v1 or None


def article_snippet_json(av, placeholder_if_invalid=True):
    """return the *valid* article snippet json for the given article version.
    if `placeholder_if_invalid=True` and article is invalid, return a stubby 'placeholder'"""
    return (
        av.article_json_v1_snippet or placeholder(av)
        if placeholder_if_invalid
        else None
    )


#
# latest article versions
#


def validate_pagination_params(page, per_page, order):
    order = str(order).strip().upper()
    # TODO: necessary? this duplicates api_v2_views.request_args a bit ...
    ensure(
        str(order).upper() in ["ASC", "DESC"],
        "unknown ordering, expecting either 'asc' or 'desc'",
    )
    ensure(
        all(map(utils.isint, [page, per_page])),
        "'page' and 'per-page' must be integers",
    )
    return page, per_page, order


def latest_published_article_versions(page=1, per_page=-1, order="DESC"):
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

    ORDER BY datetime_published %s, pa.manuscript_id %s""" % (
        order,
        order,
    )

    with connection.cursor() as cursor:
        total_sql = "select COUNT(*) from (%s) as subq" % sql
        cursor.execute(total_sql)
        total = cursor.fetchone()[0]

    if per_page > 0:
        sql += """

    LIMIT %s

    OFFSET %s""" % (
            limit,
            offset,
        )

    q = models.ArticleVersion.objects.raw(sql)

    return total, list(q)


def latest_unpublished_article_versions(page=1, per_page=-1, order="DESC"):
    start = (page - 1) * per_page
    end = start + per_page
    order_by = ["datetime_published", "article__manuscript_id"]
    if order == "DESC":
        order_by = ["-" + o for o in order_by]

    q = (
        models.ArticleVersion.objects.select_related("article")
        .annotate(max_version=Max("article__articleversion__version"))
        .filter(version=F("max_version"))
        .order_by(*order_by)
    )

    total = q.count()

    if per_page > 0:
        q = q[start:end]

    return total, list(q)


def latest_article_version_list(page=1, per_page=-1, order="DESC", only_published=True):
    "returns a list of the most recent article versions for all articles."
    args = validate_pagination_params(page, per_page, order)
    if only_published:
        return latest_published_article_versions(*args)
    return latest_unpublished_article_versions(*args)


def most_recent_article_version(msid, only_published=True):
    "returns the most recent ArticleVersion for the given manuscript id"
    try:
        latest = (
            models.ArticleVersion.objects.select_related("article")
            .filter(article__manuscript_id=msid)
            .order_by("-version")
        )

        if only_published:
            latest = latest.exclude(datetime_published=None)

        return latest[0]
    except IndexError:
        raise models.Article.DoesNotExist()


def article_version(msid, version, only_published=True):
    "returns the specified article version for the given article id"
    try:
        qs = (
            models.ArticleVersion.objects.select_related("article")
            .filter(version=version)
            .filter(article__manuscript_id=msid)
        )
        if only_published:
            qs = qs.exclude(datetime_published=None)
        return qs[0]
    except IndexError:
        # raise an AV DNE because they asked for a version specifically
        raise models.ArticleVersion.DoesNotExist()


def article_version_list(msid, only_published=True):
    "returns a list of article versions for the given article id"
    qs = (
        models.ArticleVersion.objects.select_related("article")
        .filter(article__manuscript_id=msid)
        .order_by("version")
    )
    if only_published:
        qs = qs.exclude(datetime_published=None)
    if not qs.count():
        raise models.Article.DoesNotExist()
    return qs


def relationships(msid, only_published=True):
    "returns all relationships for the given `msid`"
    av = most_recent_article_version(msid, only_published)

    extr = relation_logic.external_relationships_for_article_version(av)
    intr = relation_logic.internal_relationships_for_article_version(av)

    # the internal relationships must be snippets of the latest version of that article
    def relation_snippet(art):
        try:
            return article_snippet_json(
                most_recent_article_version(art.manuscript_id, only_published)
            )
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


def relationships2(msid, only_published=True):
    "returns all relationships for the given `msid`"

    # we can do the SQL queries without this, but we need a DoesNotExist to be raised
    # if the msid does not exist (or has not been published) yet.
    # it also simplifies the raw SQL slightly at the expense of an extra db query.
    av = most_recent_article_version(msid, only_published)
    
    # returns a list of citations
    extr_params = [
        AsIs("AND datetime_published IS NOT NULL" if only_published else ""),
        msid, #av.id,
    ]
    extr = execute_sql("external-relationships-for-msid.sql", extr_params)

    # returns article-json snippets
    intr_params = [
        av.id,
        AsIs("AND datetime_published IS NOT NULL" if only_published else ""),
    ]
    intr = execute_sql("internal-relationships-for-msid.sql", intr_params)

    # returns article-json snippets
    intr_rev_params = [
        AsIs("AND datetime_published IS NOT NULL" if only_published else ""),
        msid, #av.id,
    ]
    intr_rev = execute_sql("internal-reverse-relationships-for-msid.sql", intr_rev_params)

    extr = [i["citation"] for i in extr]
    intr = [i["article_json_v1_snippet"] or "null" for i in intr]
    intr_rev = [i["article_json_v1_snippet"] or "null" for i in intr_rev]

    data = json.loads("[%s]" % (",".join(extr + intr + intr_rev),))
    
    return data


#
#
#


def date_received(art):
    # the date received, scraped from the xml, is guaranteed to not exist for certain article types.
    # the initial quality check date will not exist under certain circumstances:
    # James@2017-03-17: "there are some instances in the archive where articles were essentially first submitted as full submissions rather than initial submissions, due to appeals or previous interactions etc. The logic we've been using for PoA is that if there is no initial qc date, use the full qc date."
    dt = firstnn([art.date_received, art.date_initial_qc, art.date_full_qc])
    return utils.to_date(dt)


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
        (art.rev4_decision, art.date_rev4_decision),
    ]
    dt = second(firstnn([pair for pair in attrs if pair[0] == models.AF]))
    return utils.to_date(dt)


EXCLUDE_RECEIVED_ACCEPTED_DATES = [models.EDITORIAL, models.INSIGHT]

#  @qdebug # 3 queries @ ~13ms local psql
def article_version_history__v1(msid, only_published=True):
    "returns a list of snippets for the history of the given article"
    article = models.Article.objects.get(manuscript_id=msid)
    avl = article.articleversion_set.all()
    if only_published:
        avl = avl.exclude(datetime_published=None)

    if not avl.count():
        # no article versions available, fail
        raise models.Article.DoesNotExist()

    struct = {
        "received": date_received(article),
        "accepted": date_accepted(article),
        "versions": lmap(article_snippet_json, avl),
    }

    if article.type in EXCLUDE_RECEIVED_ACCEPTED_DATES:
        struct = exsubdict(struct, ["received", "accepted"])

    return struct


#  @qdebug # 2 queries @ ~10ms local psql
def article_version_history__v2(msid, only_published=True):
    """returns a list of snippets for the history of the given article.
    v2 of this functions also returns pre-print events.
    returns None if no version history found."""

    q = models.ArticleVersion.objects.select_related("article").filter(
        article__manuscript_id=msid
    )
    if only_published:
        q = q.exclude(datetime_published=None)

    avl = list(q)
    if not avl:
        return

    article = q[0].article

    events = []
    for preprint in article.articleevent_set.filter(
        event=models.DATE_PREPRINT_PUBLISHED
    ):
        events.append(
            {
                "status": "preprint",
                "description": preprint.value,
                "uri": preprint.uri,
                "date": preprint.datetime_event,
            }
        )

    struct = {
        "received": date_received(article),
        "accepted": date_accepted(article),
        "versions": events + lmap(article_snippet_json, avl),
    }

    if article.type in EXCLUDE_RECEIVED_ACCEPTED_DATES:
        struct = exsubdict(struct, ["received", "accepted"])

    return struct
