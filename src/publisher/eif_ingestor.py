import json, copy
import models
from utils import subdict, exsubdict, todt, delall, msid2doi, doi2msid
import logging
import requests
from datetime import datetime
from django.conf import settings
from django.db import transaction, IntegrityError
from functools import partial

LOG = logging.getLogger(__name__)

def striptz(dtstr):
    "strips the timezone component of a stringified datetime"
    return dtstr[:dtstr.find('T')]

def import_article_version(article, article_data, create=True, update=False):
    expected_keys = ['title', 'version', 'update', 'pub-date', 'status']
    kwargs = subdict(article_data, expected_keys)

    try:
        doi = article_data['doi']
        version = int(kwargs['version'])
        version_date = kwargs.get('update')
        datetime_published = kwargs['pub-date']
        
        context = {'article': doi, 'version': version}
        LOG.info("importing ArticleVersion", extra=context)

        if version_date and version == 1:
            # this is so common it's not even worth a debug
            #LOG.warn("inconsistency: a v1 has an 'update' date", extra=context)

            d1, d2 = striptz(version_date), striptz(datetime_published)
            if d1 != d2:
                c = {}; c.update(context);
                c.update({'pub-date': datetime_published, 'update': version_date})
                LOG.warn("double inconsistency: not only do we have an 'update' date for a v1, it doesn't match the date published", extra=c)

                # 'update' date occurred before publish date ...
                if d1 < d2:
                    LOG.warn("triple inconsistency: not only do we have an 'update' date for a v1 that doesn't match the date published, it was actually updated *before* it was published", extra=c)

        if version == 1:
            version_date = datetime_published

        if not version_date and version > 1:
            LOG.warn("inconsistency: a version > 1 does not have an 'update' date", extra=context)
            if settings.FAIL_ON_NO_UPDATE_DATE:
                msg = "no 'update' date found for ArticleVersion"
                raise ValueError(msg)
            msg = "no 'update' date found for ArticleVersion, using None instead"
            LOG.warn(msg, extra=context)
            version_date = None

        # post process data
        kwargs.update({
            'article':  article,
            'version': version,
            'datetime_published': todt(version_date),
            'status': kwargs['status'].lower(),
        })
        delall(kwargs, ['pub-date', 'update'])
    except KeyError:
        LOG.error("expected keys invalid/not present", \
                      extra={'expected_keys': expected_keys})
        raise

    try:
        avobj = models.ArticleVersion.objects.get(article=article, version=kwargs['version'])
        if not update:
            msg = "Article with version does exists but update == False"
            LOG.warn(msg, extra=context)
            raise AssertionError(msg)
        LOG.debug("ArticleVersion found, updating")
        for key, val in kwargs.items():
            setattr(avobj, key, val)
        avobj.save()
        LOG.info("updated existing ArticleVersion", extra=context)
        return avobj
    
    except models.ArticleVersion.DoesNotExist:
        if not create:
            msg = "ArticleVersion with version does not exist and create == False"
            LOG.warn(msg, extra=context)
            raise

    LOG.debug("ArticleVersion NOT found, creating", extra=context)
    avobj = models.ArticleVersion(**kwargs)
    avobj.save()
    LOG.info("created new ArticleVersion", extra=context)
    return avobj

def import_article(journal, article_data, create=True, update=False):
    if not article_data or not isinstance(article_data, dict):
        raise ValueError("given data to import is empty/invalid")
    expected_keys = ['doi', 'volume', 'path', 'article-type', 'manuscript_id']

    # data wrangling
    try:
        kwargs = subdict(article_data, expected_keys)

        # JATS XML doesn't contain the manuscript ID. derive it from doi
        if not kwargs.has_key('manuscript_id') and kwargs.has_key('doi'):
            kwargs['manuscript_id'] = doi2msid(kwargs['doi'])

        elif not kwargs.has_key('doi') and kwargs.has_key('manuscript_id'):
            kwargs['doi'] = msid2doi(kwargs['manuscript_id'])

        context = {'article': kwargs['doi']}

        LOG.info("importing Article", extra=context)

        # post process data
        kwargs.update({
            'journal':  journal,
            'volume': int(kwargs['volume']),
            'type': kwargs['article-type'],
        })
        delall(kwargs, ['path', 'article-type'])
    except KeyError:
        raise ValueError("expected keys invalid/not present: %s" % ", ".join(expected_keys))
    
    # attempt to insert
    article_key = subdict(kwargs, ['doi', 'version'])
    try:
        article_obj = models.Article.objects.get(**article_key)
        avobj = import_article_version(article_obj, article_data, create, update)
        LOG.info("Article exists, updating", extra=context)
        for key, val in kwargs.items():
            setattr(article_obj, key, val)
        article_obj.save()
        return article_obj, avobj

    except models.Article.DoesNotExist:
        # we've been told not to create new articles.
        # this is now a legitimate exception
        if not create:
            raise
    article_obj = models.Article(**kwargs)
    article_obj.save()
    avobj = import_article_version(article_obj, article_data, create, update)
    LOG.info("created new Article %s" % article_obj)
    return article_obj, avobj

def import_article_from_json_path(journal, article_json_path, *args, **kwargs):
    "convenience function. loads the article data from a json file"
    return import_article(journal, json.load(open(article_json_path, 'r')), *args, **kwargs)

#
# 'patch'
#

def patch(data, update=True):
    "given partial article/articleversion data, updates that article"
    data = copy.deepcopy(data)
    
    doi, version_patches = map(data.pop, ['doi', 'versions'])
    context = {'article': doi, 'patch_data': data, 'version_patch_data': version_patches}
    try:
        art = models.Article.objects.get(doi=doi)
        if not update:
            return True
        with transaction.atomic():
            # patch article
            for key, val in data.items():
                setattr(art, key, val)
            art.save()

            # patch any versions
            for data in version_patches:
                version = data['version']
                context['version'] = version
                av = art.articleversion_set.get(version=version)
                for key, val in data.items():
                    setattr(av, key, val)
                av.save()
        LOG.info("successfully patched Article", extra=context)
        return True

    except models.Article.DoesNotExist:
        LOG.warn("Article not found, skipping patch", extra=context)
        return False

    except models.ArticleVersion.DoesNotExist:
        LOG.warn("ArticleVersion not found, skipping patch", extra=context)
        return False

    except IntegrityError as err:
        LOG.error(err)
        raise

def patch_handler(journal, path, create, update):
    json_patches = open(path, 'r').readlines()
    patch_list = map(json.loads, json_patches)
    return map(partial(patch, update), patch_list)
