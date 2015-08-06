import json
import models
from utils import subdict
import logging
import requests
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

def todt(val):
    naive = datetime.strptime(val, "%Y-%m-%d")
    return pytz.utc.localize(naive)

def import_article(journal, article_data, update=False):
    if not article_data:
        return None
    kwargs = subdict(article_data, ['title', 'version', 'doi', 'volume', 'pub-date', 'path', 'status', 'article-type'])
    kwargs.update({
        'journal':  journal,
        'version': int(kwargs['version']),
        'datetime_published': todt(kwargs['pub-date']),
        'volume': int(kwargs['volume']),
        'status': kwargs['status'].lower(),
        'website_path': kwargs['path'],
        'type': kwargs['article-type'],
    })
    del kwargs['pub-date']
    del kwargs['path']
    del kwargs['article-type']
    try:
        article_obj = models.Article.objects.get(doi=kwargs['doi'])
        if update:
            logger.info("article exists, updating")
            for key, val in kwargs.items():
                setattr(article_obj, key, val)
            article_obj.save()
        else:
            logger.warning("article exists, not importing")   
        return article_obj
    except models.Article.DoesNotExist:
        pass
    article_obj = models.Article(**kwargs)
    article_obj.save()
    logger.info("created new Article %s" % article_obj)
    return article_obj

def import_article_from_json_path(journal, article_json_path):
    "convenience function. loads the article data from a json file"
    return import_article(journal, json.load(open(article_json_path, 'r')))

#
# import article from a github repo
# this is tied to eLife right now, but there is some code to make this more robust:
# src/publisher/super_lazy_repo_lookup.py
#

def github_url(doi):
    if '/' in doi:
        # we have a full doi
        fname = "%s.xml.json" % doi.lower().split('/')[1].replace('.', '')
    else:
        # assume we have a pub-id (doi sans publisher id, the 'eLife.00003' in the '10.7554/eLife.00003'
        fname = doi.replace('.', '') + ".xml.json"
    return "https://raw.githubusercontent.com/elifesciences/elife-article-json/master/article-json/" + fname

def fetch_url(url):
    try:
        logger.info("fetching url %r", url)
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

def import_article_from_github_repo(journal, doi):
    if not doi or not str(doi).strip():
        raise ValueError("bad doi") # todo - shift into a utility?
    return import_article(journal, fetch_url(github_url(doi)))
