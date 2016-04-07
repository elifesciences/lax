
import json
import models
from utils import subdict, todt, delall
import logging
import requests
from datetime import datetime

LOG = logging.getLogger(__name__)

def import_article_version(article, article_data, create=True, update=False):
    expected_keys = ['version', 'pub-date', 'status']
    try:
        kwargs = subdict(article_data, expected_keys)
        # post process data
        kwargs.update({
            'article':  article,
            'version': int(kwargs['version']),
            'datetime_published': todt(kwargs['pub-date']),
            'status': kwargs['status'].lower(),
        })
        delall(kwargs, ['pub-date'])
    except KeyError:
        raise ValueError("expected keys invalid/not present: %s" % ", ".join(expected_keys))
    
    try:
        avobj = models.ArticleVersion.objects.get(article=article, version=kwargs['version'])
        if not update:
            raise AssertionError("article with version exists and I've been told not to update.")
        LOG.info("ArticleVersion found, updating")
        for key, val in kwargs.items():
            setattr(avobj, key, val)
        avobj.save()
        return avobj
    
    except models.ArticleVersion.DoesNotExist:
        if not create:
            raise
    LOG.info("ArticleVersion NOT found, creating")
    avobj = models.ArticleVersion(**kwargs)
    avobj.save()
    LOG.info("created new ArticleVersion %s" % avobj)
    return avobj

def import_article(journal, article_data, create=True, update=False):
    if not article_data or not isinstance(article_data, dict):
        raise ValueError("given data to import is empty/invalid")
    expected_keys = ['title', 'doi', 'volume', 'path', 'article-type']

    # data wrangling
    try:
        kwargs = subdict(article_data, expected_keys)
        # post process data
        kwargs.update({
            'journal':  journal,
            'volume': int(kwargs['volume']),
            'website_path': kwargs['path'],
            'type': kwargs['article-type'],
        })
        delall(kwargs, ['path', 'article-type'])
    except KeyError:
        raise ValueError("expected keys invalid/not present: %s" % ", ".join(expected_keys))
    
    # attempt to insert
    article_key = subdict(kwargs, ['doi', 'version'])
    try:
        article_obj = models.Article.objects.get(**article_key)
        import_article_version(article_obj, article_data, create, update)
        LOG.info("article exists, updating")
        for key, val in kwargs.items():
            setattr(article_obj, key, val)
        article_obj.save()
        return article_obj

    except models.Article.DoesNotExist:
        # we've been told not to create new articles.
        # this is now a legitimate exception
        if not create:
            raise
    article_obj = models.Article(**kwargs)
    article_obj.save()
    import_article_version(article_obj, article_data, create, update)
    LOG.info("created new Article %s" % article_obj)
    return article_obj

def import_article_from_json_path(journal, article_json_path, *args, **kwargs):
    "convenience function. loads the article data from a json file"
    return import_article(journal, json.load(open(article_json_path, 'r')), *args, **kwargs)

#
# import article from a github repo
# this is tied to eLife right now, but there is some code to make this more robust:
# src/publisher/super_lazy_repo_lookup.py
#

def github_url(doi, version=None):
    assert version == None, "fetching specific versions of articles from github is not yet supported!"
    if '/' in doi:
        # we have a full doi
        fname = "%s.xml.json" % doi.lower().split('/')[1].replace('.', '')
    else:
        # assume we have a pub-id (doi sans publisher id, the 'eLife.00003' in the '10.7554/eLife.00003'
        fname = doi.replace('.', '') + ".xml.json"
    return "https://raw.githubusercontent.com/elifesciences/elife-article-json/master/article-json/" + fname

def fetch_url(url):
    try:
        LOG.info("fetching url %r", url)
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            logging.warning("given url %r returned a 404", url)
    except ValueError:
        logging.warning("got a response but it wasn't json")
    except:
        logging.exception("unhandled exception attempting to fetch url %r", url)
        raise

def import_article_from_github_repo(journal, doi, version=None):
    if not doi or not str(doi).strip():
        raise ValueError("bad doi") # todo - shift into a utility?
    return import_article(journal, fetch_url(github_url(doi, version)))
