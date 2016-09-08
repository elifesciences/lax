import copy
from publisher import models, utils
from publisher.utils import subdict, exsubdict
import logging
from django.db import transaction
from et3 import render
from et3.extract import path as p

LOG = logging.getLogger(__name__)

class StateError(RuntimeError):
    pass

#
# make the article-json lax compatible
# receives a list of article-json
#

JOURNAL = {
    'name': [p('title')],
}
ARTICLE = {
    'journal': [p('journal')], # a models.Journal object is injected into the source data
    'manuscript_id': [p('id'), int],
    'volume': [p('volume')],
    'type': [p('type')],
}
ARTICLE_VERSION = {
    'article': [p('article')], # a models.Article object is injected into the source data
    'title': [p('title')],
    'version': [p('version')],
    'status': [models.POA],
    'datetime_published': [p('published'), utils.todt],
}

#
#
#

def create_or_update(Model, data, key_list, create=True, update=True, commit=True):
    inst = None
    created = updated = False
    try:
        # try and find an entry of Model using the key fields in the given data
        inst = Model.objects.get(**subdict(data, key_list))
        # object exists, otherwise DoesNotExist would have been raised
        if update:
            [setattr(inst, key, val) for key, val in data.items()]
            updated = True
    except Model.DoesNotExist:
        if create:
            inst = Model(**data)
            created = True

    if (updated or created) and commit:
        inst.save()
    
    # it is possible to neither create nor update.
    # in this case if the model cannot be found then None is returned: (None, False, False)
    return (inst, created, updated)

@transaction.atomic
def ingest(data, force=False):
    """ingests article-json. returns a triple of (journal obj, article obj, article version obj)

    unpublished article-version data can be ingested multiple times UNLESS that article version has been published.

    published article-version data can be ingested only if force=True"""

    data = copy.deepcopy(data) # we don't want to modify the given data
    
    create = update = True
    log_context = {}
    
    try:
        journal_struct = render.render_item(JOURNAL, data['journal'])
        journal, created, updated = \
          create_or_update(models.Journal, journal_struct, ['name'], create, update)
        
        assert isinstance(journal, models.Journal)
        log_context['journal'] = journal

        data['article']['journal'] = journal
        article_struct = render.render_item(ARTICLE, data['article'])
        article, created, updated = \
          create_or_update(models.Article, article_struct, ['msid', 'journal'], create, update)

        assert isinstance(article, models.Article)
        log_context['article'] = article

        # this is an INGEST event, not a PUBLISH event. we don't touch the date published. see `publish()`
        av_ingest_description = exsubdict(ARTICLE_VERSION, ['datetime_published'])
        data['article']['article'] = article
        av_struct = render.render_item(av_ingest_description, data['article'])
        av, created, update = \
          create_or_update(models.ArticleVersion, av_struct, ['article', 'version'], create, update, commit=False)

        assert isinstance(av, models.ArticleVersion)
        log_context['article-version'] = av

        if created:
            # brand new (unpublished) article version. nothing to worry about.
            pass
        
        elif updated:
            # this version of the article already exists
            # this is only a problem if the article version has already been published
            if av.datetime_published:
                # uhoh. we've received an INGEST event for a previously published article
                if not force:
                    # unless our arm is being twisted, die.
                    raise StateError("refusing to ingest new article data on an already published article version.")

        # passed all checks, save
        av.save()
        return journal, article, av
    
    except Exception as err:
        LOG.exception("unhandled exception attempting to ingest article-json", extra=log_context)
        raise err

#
#
#

def publish(msid, version, datetime_published=None, force=False):
    """attach a `datetime_published` value to an article version. if none provided, use RIGHT NOW.
    you cannot publish an already published article version unless force==True"""
    # ensure we have a utc datetime
    if not datetime_published:
        datetime_published = utils.utcnow()
    else:
        # ensure given datetime is in utc
        datetime_published = utils.todt(datetime_published)
    av = models.ArticleVersion.objects.get(article__manuscript_id=msid, version=version)
    if av.published() and not force:
        raise StateError("refusing to publish an already published article")
    av.datetime_published = datetime_published
    av.save()
    return av
