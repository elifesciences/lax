import os, requests
import models
from django.conf import settings
import logging
from publisher import ingestor, utils
from publisher.utils import first, second
from datetime import datetime
from django.utils import timezone
from django.db.models import ObjectDoesNotExist, Max, F, Q

LOG = logging.getLogger(__name__)

def journal(name=None):
    journal = {'name': name}
    if not name:
        journal = settings.PRIMARY_JOURNAL
    if journal.has_key('inception') and timezone.is_naive(journal['inception']):
        journal['inception'] = timezone.make_aware(journal['inception'])
    obj, new = models.Journal.objects.get_or_create(**journal)
    if new:
        LOG.info("created new Journal %s", obj)
    return obj

def article(doi, version=None, lazy=True):
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

def create_attribute(**kwargs):
    at = models.AttributeType(**kwargs)
    at.save()
    return at

def get_attribute(article_obj, attr):
    """looks for the attribute on the article itself first, then looks at
    the list of ad-hoc article attributes and tries to retrieve attr from there."""
    if utils.djobj_hasattr(article_obj, attr):
        return getattr(article_obj, attr)
    try:
        article_obj.articleattribute_set.get(key__name=attr)
    except models.ArticleAttribute.DoesNotExist:
        return None

def add_update_article_attribute(article, key, val, extant_only=True):
    if utils.djobj_hasattr(article, key):
        # key exists, update
        # update the article object itself
        setattr(article, key, val)
        article.save()
        return {'key': key,
                'value': getattr(article, key),
                'doi': article.doi}#,
                #'version': article.version}
    
    # get/create the attribute type
    try:
        attrtype = models.AttributeType.objects.get(name=key)
        # found
    except models.AttributeType.DoesNotExist:
        if extant_only:
            # we've been told to *not* create new types of attributes. die.
            raise
        # not found, create.
        kwargs = {
            'name': key,
            'type': models.DEFAULT_ATTR_TYPE,
            'description': "[automatically created]"
        }
        attrtype = models.AttributeType(**kwargs)
        attrtype.save()
        LOG.info("created new AttributeType %r", attrtype)
        
    # add/update the article attribute    
    kwargs = {
        'article': article,
        'key': attrtype,
        'value': val,
    }
    try:
        attr = models.ArticleAttribute.objects.get(**utils.subdict(kwargs, ['article', 'key']))
        # article already has this attribute. update it with whatever value we were given
        attr.value = val
        attr.save()

    except models.ArticleAttribute.DoesNotExist:
        # article doesn't have this particular attribute yet
        attr = models.ArticleAttribute(**kwargs)
        attr.save()

    return {'key': attrtype.name,
            'value': val,
            'doi': article.doi}#,
            #'version': article.version}

def add_or_update_article(**article_data):
    """TESTING ONLY. given article data it attempts to find the 
    article and update it, otherwise it will create it, filling
    any missing keys with dummy data. returns the created article."""
    assert article_data.has_key('doi'), "a value for 'doi' *must* exist"
    filler = [
        'title',
        'doi',
        ('volume', 1),
        'path',
        'article-type',
        ('version', 1),
        ('pub-date', '2012-01-01'),
        'status',
    ]
    article_data = utils.filldict(article_data, filler, 'pants-party')
    return ingestor.import_article(journal(), article_data, create=True, update=True)

#
#
#

def latest_article_versions():
    # 'distinct on' not supported in sqlite3 :(
    #return models.ArticleVersion.objects.all().distinct('article__doi')

    # works well across parent-child
    # http://stackoverflow.com/questions/19923877/django-orm-get-latest-for-each-group
    #Score.objects.annotate(max_date=Max('student__score__date')).filter(date=F('max_date'))

    q = models.ArticleVersion.objects.annotate(max_version=Max('article__articleversion__version')).filter(version=F('max_version'))

    # order by when article version was published, newest first
    q = q.order_by('-datetime_published')
    return q

#
#
#

def mk_dxdoi_link(doi):
    return "http://dx.doi.org/%s" % doi

def check_doi(doi):
    """ensures that the doi both exists with crossref and that it
    successfully redirects to an article on the website"""
    return requests.get(mk_dxdoi_link(doi))


def doi2msid(doi):
    "manuscript id representation. used in EJP"
    prefix = '10.7554/eLife.'
    return doi[len(prefix):].lstrip('0')


#
#
#

def record_correction(artobj, when=None):
    if when:
        assert timezone.is_aware(when), "refusing a naive datetime."
        assert timezone.now() > when, "refusing a correction made in the future"
        if artobj.journal.inception:
            assert when > artobj.journal.inception, "refusing a correction made before the article's journal started"
    correction = models.ArticleCorrection(**{
        'article': artobj,
        'datetime_corrected': when if when else datetime.now()})
    correction.save()
    return correction
