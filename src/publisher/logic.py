import os, requests
import models
from django.conf import settings
import logging
from publisher import ingestor, utils

logger = logging.getLogger(__name__)

def journal(journal_name=settings.PRIMARY_JOURNAL):
    obj, new = models.Journal.objects.get_or_create(name=journal_name)
    if new:
        logger.info("created new Journal %s", obj)
    return obj

def article(doi, version=None, lazy=True):
    try:
        if version:
            return models.Article.objects.get(doi__iexact=doi, version=version)
        return models.Article.objects.filter(doi__iexact=doi).order_by('-version')[:1][0]
    
    except (IndexError, models.Article.DoesNotExist):
        if lazy:
            return ingestor.import_article_from_github_repo(journal(), doi)
        raise

def create_attribute(**kwargs):
    at = models.AttributeType(**kwargs)
    at.save()
    return at

def add_attribute_to_article(article, key, val, extant_only=True):
    try:
        attrtype = models.AttributeType.objects.get(name=key)
    except models.AttributeType.DoesNotExist:
        if extant_only:
            raise
        attrtype = models.AttributeType(name=key, type=models.DEFAULT_ATTR_TYPE, description="[automatically created]")
        attrtype.save()
    kwargs = {
        'article': article,
        'key': attrtype,
        'value': val,
    }
    attr = models.ArticleAttribute(**kwargs)
    attr.save()
    return attr

def get_attribute(article_obj, attr):
    """looks for the attribute on the article itself first, then looks at
    the list of ad-hoc article attributes and tries to retrieve attr from there."""
    if utils.djobj_hasattr(article_obj, attr):
        return getattr(article_obj, attr)
    try:
        article_obj.articleattribute_set.get(key__slug=attr)
    except models.ArticleAttribute.DoesNotExist:
        return None

def add_update_article_attribute(article, key, val, extant_only=True):
    if utils.djobj_hasattr(article, key):
        setattr(article, key, val)
        article.save()
    else:
        add_attribute_to_article(article, key, val, extant_only)
    return article

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
