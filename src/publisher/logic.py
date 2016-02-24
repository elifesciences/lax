import os, requests
import models
from django.conf import settings
import logging
from publisher import ingestor, utils

LOG = logging.getLogger(__name__)

def journal(journal_name=settings.PRIMARY_JOURNAL):
    obj, new = models.Journal.objects.get_or_create(name=journal_name)
    if new:
        LOG.info("created new Journal %s", obj)
    return obj

def article(doi, version=None, lazy=True):
    """returns the latest version of the article identified by the
    doi, or the specific version given.
    Raises DoesNotExist if article not found."""
    try:
        if version:
            return models.Article.objects.get(doi__iexact=doi, version=version)
        return models.Article.objects.filter(doi__iexact=doi).order_by('-version')[:1][0]
    
    except (IndexError, models.Article.DoesNotExist):
        # TODO: and doi-looks-like-an-elife-doi
        # TODO: fetching articles lazily only works when a version is not specified. articles in the github repo have no version currently.
        if lazy and version == None:
            try:
                ingestor.import_article_from_github_repo(journal(), doi, version)
                return article(doi, version, lazy=False)
            except ValueError:
                # bad data, bad doi, etc
                pass
        raise models.Article.DoesNotExist()

def article_versions(doi):
    "returns all versions of the given article"
    return models.Article.objects.filter(doi__iexact=doi)

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
        # update the article object itself
        setattr(article, key, val)
        article.save()
        return {'key': key,
                'value': getattr(article, key),
                'doi': article.doi,
                'version': article.version}
    
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
            'doi': article.doi,
            'version': article.version}

def add_or_update_article(**article_data):
    """given a article data it attempts to find the article and update it,
    otherwise it will create it. return the created article"""
    assert article_data.has_key('doi'), "a value for 'doi' *must* exist"
    try:
        art = models.Article.objects.get(doi=article_data['doi'], version=article_data['version'])
        for key, val in article_data.items():
            setattr(art, key, val)
        art.save()

    except models.Article.DoesNotExist:
        art = models.Article(**article_data)
        art.save()

    return art

#
#
#

def mk_dxdoi_link(doi):
    return "http://dx.doi.org/%s" % doi

def check_doi(doi):
    """ensures that the doi both exists with crossref and that it
    successfully redirects to an article on the website"""
    return requests.get(mk_dxdoi_link(doi))
