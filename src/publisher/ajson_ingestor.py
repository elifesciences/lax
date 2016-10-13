import copy
from publisher import models, utils
from publisher.utils import subdict
import logging
from django.db import transaction
from et3 import render
from et3.extract import path as p, val
from django.db import IntegrityError
import json
import boto3
from django.dispatch import receiver
from django.db.models.signals import pre_save
from django.conf import settings
from functools import partial

LOG = logging.getLogger(__name__)

class StateError(RuntimeError):
    pass

'''
def remove(keys):
    def fn(v):
        return utils.exsubdict(v, keys)
    return fn
'''

#
# make the article-json lax compatible
# receives a list of article-json
#

JOURNAL = {
    'name': [p('title')],
}
ARTICLE = {
    'manuscript_id': [p('id'), int],
    'volume': [p('volume')],
    'type': [p('type')],
    'doi': [p('id'), utils.msid2doi], # remove when apiv1 is turned off
    #'ejp_type': [p('type'), models.EJP_TYPE_REV_SLUG_IDX.get]
}
ARTICLE_VERSION = {
    'title': [p('title')],
    'version': [p('version')],
    'status': [models.POA],
    # only v1 article-json has a published date. v2 article-json does not
    'datetime_published': [p('published', None), utils.todt],
    'article_json_v1_raw': [val],  # , remove('snippet')],
    #'article_json_v1_snippet': [p('snippet')], # urgh, how to do this?
}

def atomic(fn):
    def wrapper(*args, **kwargs):
        result, rollback_key = None, 'dry run rollback'
        # NOTE: dry_run must always be passed as keyword parameter (dry_run=True)
        dry_run = kwargs.pop('dry_run', False)
        try:
            with transaction.atomic():
                result = fn(*args, **kwargs)
                if dry_run:
                    # `transaction.rollback()` doesn't work here because the `transaction.atomic()`
                    # block is expecting to do all the work and only rollback on exceptions
                    raise IntegrityError(rollback_key)
                return result
        except IntegrityError as err:
            if dry_run and err.message == rollback_key:
                return result
            # this was some other IntegrityError
            raise
    return wrapper

#
#
#

#@cache # ?
def event_bus_conn():
    sns = boto3.resource('sns')
    topic = sns.Topic(settings.SNS_TOPIC_ARN)
    return topic

def notify_event_bus(art):
    "notify the event bus when this article or one of it's versions has been changed in some way"
    if settings.DEBUG:
        return
    try:
        msg = {"type": "article", "id": art.manuscript_id}
        msg_json = json.dumps({'default': msg})
        LOG.debug("writing message to event bus", extra={'bus-message': msg_json})
        event_bus_conn().publish(Message=msg_json, MessageStructure='json')
    except ValueError as err:
        # probably serializing value
        LOG.error("failed to serialize event bus payload %s", err, extra={'bus-message': msg_json})

    except Exception as err:
        LOG.error("unhandled error attempting to notify event bus of article change: %s", err)

#
#
#

def create_or_update(Model, orig_data, key_list, create=True, update=True, commit=True, **overrides):
    inst = None
    created = updated = False
    data = {}
    data.update(orig_data)
    data.update(overrides)
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

def _ingest(data, force=False):
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

        article_struct = render.render_item(ARTICLE, data['article'])
        article, created, updated = \
            create_or_update(models.Article, article_struct, ['manuscript_id', 'journal'], create, update, journal=journal)

        assert isinstance(article, models.Article)
        log_context['article'] = article

        previous_article_versions = None
        if updated:
            previous_article_versions = list(article.articleversion_set.all().order_by('version')) # earliest -> latest

        # this is an INGEST event and *not* a PUBLISH event. we don't touch the date published.
        av_struct = render.render_item(ARTICLE_VERSION, data['article'])
        del av_struct['datetime_published']

        av, created, update = \
            create_or_update(models.ArticleVersion, av_struct, ['article', 'version'],
                             create, update, commit=False, article=article)

        assert isinstance(av, models.ArticleVersion)
        log_context['article-version'] = av

        # enforce business rules

        if created:
            if previous_article_versions:
                last_version = previous_article_versions[-1]
                log_context['previous-version'] = last_version

                if not last_version.published():
                    # uhoh. we're attempting to create an article version before previous version of that article has been published.
                    msg = "refusing to ingest new article version when previous article version is still unpublished."
                    LOG.error(msg, extra=log_context)
                    raise StateError(msg)

                if not last_version.version + 1 == av.version:
                    # uhoh. we're attempting to create an article version out of sequence
                    msg = "refusing to ingest new article version out of sequence."
                    log_context.update({
                        'given-version': av.version,
                        'expected-version': last_version.version + 1})
                    LOG.error(msg, extra=log_context)
                    raise StateError(msg)

            # no other versions of article exist
            else:
                if not av.version == 1:
                    # uhoh. we're attempting to create our first article version and it isn't a version 1
                    msg = "refusing to ingest new article version out of sequence. no other article versions exist so I expect a v1"
                    log_context.update({
                        'given-version': av.version,
                        'expected-version': 1})
                    LOG.error(msg, extra=log_context)
                    raise StateError(msg)

        elif updated:
            # this version of the article already exists
            # this is only a problem if the article version has already been published
            if av.published():
                # uhoh. we've received an INGEST event for a previously published article version
                if not force:
                    # unless our arm is being twisted, die.
                    msg = "refusing to ingest new article data on an already published article version."
                    LOG.error(msg, extra=log_context)
                    raise StateError(msg)

        transaction.on_commit(partial(notify_event_bus, article))

        # passed all checks, save
        av.save()

        return journal, article, av

    except StateError:
        raise

    except Exception:
        LOG.exception("unhandled exception attempting to ingest article-json", extra=log_context)
        raise

@atomic
def ingest(*args, **kwargs):
    return _ingest(*args, **kwargs)


#
# PUBLISH requests
#

def _publish(msid, version, force=False):
    """attach a `datetime_published` value to an article version. if none provided, use RIGHT NOW.
    you cannot publish an already published article version unless force==True"""
    try:
        av = models.ArticleVersion.objects.get(article__manuscript_id=msid, version=version)
        if av.published():
            if not force:
                raise StateError("refusing to publish an already published article version")

        # the json *will* have a pub date if it's a v1 ...
        if version == 1:
            datetime_published = utils.todt(av.article_json_v1_raw.get('published'))
            if not datetime_published:
                raise StateError("failed to pull pubdate from from ingested article json")

        else:
            # but *not* if it's > v1. in this case, we generate one.
            if av.published() and force:
                # this article version is already published and a force publish request has been sent
                # what is the expected action? a new pubdate of `now`?
                # because the pub date isn't passed in the article json, we can't set an arbitrary one
                pass
            datetime_published = utils.utcnow()

        av.datetime_published = datetime_published
        av.save()
        return av
    except models.ArticleVersion.DoesNotExist:
        # attempted to publish an article that doesn't exist ...
        raise StateError("refusing to publish an article '%sv%s' that doesn't exist" % (msid, version))

@atomic
def publish(*args, **kwargs):
    return _publish(*args, **kwargs)

#
# INGEST+PUBLISH requests
#

@atomic
def ingest_publish(data, force=False, dry_run=False):
    "convenience. publish an article if it were successfully ingested"
    j, a, av = _ingest(data, force=force)
    return j, a, _publish(a.manuscript_id, av.version, force=force)

#
# article json wrangling
# https://docs.djangoproject.com/en/1.9/ref/signals/#pre-save
#

@receiver(pre_save, sender=models.ArticleVersion)
def merge_validate_article_json(sender, instance, **kwargs):
    # 1. merge disparate json snippets
    # 2. validate
    # 3. if valid, update json field, set valid=True
    pass
