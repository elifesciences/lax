import models
from django.conf import settings
import logging
from publisher import eif_ingestor, utils
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
            return article, article.articleversion_set.get(version=version)
        return article, article.articleversion_set.latest('version')
    except ObjectDoesNotExist:
        raise models.Article.DoesNotExist()

def article_versions(doi):
    "returns all versions of the given article"
    return models.ArticleVersion.objects.filter(article__doi__iexact=doi)


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

# TODO: rename `latest_article_version_list`
def latest_article_versions(only_published=True):
    "returns a most recent article versions of all articles"

    # 'distinct on' not supported in sqlite3 :(
    # return models.ArticleVersion.objects.all().distinct('article__doi')

    #
    # THIS FUNCTION ISN'T WORKING AS EXPECTED
    # the max() function is not taking into account excluded unpublished articles being
    #

    q = models.ArticleVersion.objects \
        .select_related('article')

    if only_published:
        #q = q.exclude(article__articleversion__datetime_published=None)
        q = q.exclude(datetime_published=None)
        #q = q.annotate(max_version=When(~Q(article__articleversion__datetime_published=None), then=F('article__articleversion__version')))
        pass

    q = q.annotate(max_version=Max('article__articleversion__version'))
    q = q.filter(version=F('max_version')) \
        .order_by('-datetime_published')

    # print str(q.query)

    return q

def most_recent_article_version(msid, only_published=True):
    "returns the most recent article version for the given article id"
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

#
#
#

def article_version_history(msid, only_published=True):
    "returns a struct for the history of the given article"
    article = models.Article.objects.get(manuscript_id=msid)
    avl = article.articleversion_set.all()
    if only_published:
        avl = avl.exclude(datetime_published=None)

    def version_row(av):
        return {
            'status': av.status,
            'published': av.datetime_published,
            'version': av.version
        }
    return {
        'received': article.date_initial_qc,
        'accepted': article.date_accepted,
        'versions': map(version_row, avl)
    }

def bulk_article_version_history(only_published=True):
    for art in models.Article.objects.all():
        result = article_version_history(art.manuscript_id, only_published)
        result['msid'] = art.manuscript_id
        yield result

#
#
#

def article_json(av):
    "returns the *valid* article json for the given article version."
    # TODO: obviously this is just a placeholder.
    # this function is expected to:
    # merge any snippets of models.Article json over the top of the models.ArticleVersion raw json
    # save the result in the models.ArticleVersion actual json field (?)
    return av.article_json_v1

def article_snippet_json(av):
    "return the *valid* article snippet json for the given article version"
    return av.article_json_v1_snippet

#
#
#

def mk_dxdoi_link(doi):
    return "http://dx.doi.org/%s" % doi
