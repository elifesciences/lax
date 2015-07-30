import os, requests
import models
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

def journal(journal_name=settings.PRIMARY_JOURNAL):
    obj, new = models.Journal.objects.get_or_create(name=journal_name)
    if new:
        logger.info("created new Journal %s", obj)
    return obj

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

#
#
#

def mk_dxdoi_link(doi):
    return "http://dx.doi.org/%s" % doi

def check_doi(doi):
    """ensures that the doi both exists with crossref and that it
    successfully redirects to an article on the website"""
    return requests.get(mk_dxdoi_link(doi))
