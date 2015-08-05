import json
import models
from utils import subdict
import logging
import requests

logger = logging.getLogger(__name__)

def import_article(journal, article_data):
    kwargs = subdict(article_data, ['title', 'version', 'doi'])
    kwargs['journal'] = journal
    kwargs['version'] = int(kwargs['version'])
    art_id = subdict(kwargs, ['doi', 'version'])
    try:
        article_obj = models.Article.objects.get(**art_id)
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
    return import_article(journal, fetch_url(github_url(doi)))
