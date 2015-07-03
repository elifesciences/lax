import os, json
import models
from utils import subdict
import logging

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
