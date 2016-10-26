import json
from dateutil import parser
from . import models, utils
from django.db import transaction

import logging
LOG = logging.getLogger(__name__)

def import_article(journal, article_data, create=True, update=False):
    article_data['journal'] = journal
    msid = article_data['manuscript_id']
    article_data['doi'] = utils.msid2doi(msid)
    art = None
    try:
        art = models.Article.objects.get(manuscript_id=msid)
        if not update:
            raise AssertionError("article with manuscript id exists and I've been told not to update.")
    except models.Article.DoesNotExist:
        # doesn't exist, we can happily create a new article
        if not create:
            LOG.error("article with manuscript id %r does *not* exist and I've been told *not* to create new articles.", msid)
            # raise

    if not art and create:
        try:
            art = models.Article(**article_data)
            art.save()
            LOG.info("created Article %r", art)
            return art
        except:
            LOG.exception("unhandled error attempting to import article from EJP: %s", article_data)
            raise

    # update article, but only if we have an article
    if update and art:
        for key, val in article_data.items():
            setattr(art, key, val)
        art.save()
        LOG.info("updated Article %r", art)
    return art

#
#
#

# http://stackoverflow.com/questions/14995743/how-to-deserialize-the-datetime-in-a-json-object-in-python
def load_with_datetime(pairs, format='%Y-%m-%d'):
    """Load with dates"""
    d = {}
    for k, v in pairs:
        if isinstance(v, basestring):
            if k.startswith('date_'):
                v = parser.parse(v)
        d[k] = v
    return d

def import_article_list_from_json_path(journal, json_path, *args, **kwargs):
    with open(json_path, 'r') as fh:
        article_list = json.load(fh, object_pairs_hook=load_with_datetime)
    with transaction.atomic():
        def fn(ad):
            try:
                return import_article(journal, ad, *args, **kwargs)
            except AssertionError as e:
                LOG.error("failed to import article with msid %r: %s", ad['manuscript_id'], e)
                LOG.error("full data %s", ad)
                raise
        map(fn, article_list)
