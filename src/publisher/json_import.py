import os, json
import models
from utils import subdict
import logging

logger = logging.getLogger(__name__)

def import_article(journal, article_json_path):
    article = json.load(open(article_json_path, 'r'))
    kwargs = subdict(article, ['title', 'version', 'doi'])
    kwargs['journal'] = journal
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
    return article
