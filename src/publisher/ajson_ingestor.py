import json
from publisher import logic, models, utils
from publisher.utils import subdict
import logging
from pprint import pprint

from et3 import render
from et3.extract import path as p, val

LOG = logging.getLogger(__name__)

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

def create_or_update(Model, data, key_list, create=True, update=True):
    inst = None
    created = updated = False
    try:
        # try and find an entry of Model using the key fields in the given data
        inst = Model.objects.get(**subdict(data, key_list))
        # object exists, otherwise DoesNotExist would have been raised
        if update:
            [setattr(inst, key, val) for key, val in data.items()]
            inst.save()
            updated = True
    except Model.DoesNotExist:
        if create:
            inst = Model(**data)
            inst.save()
            created = True
    # it is possible to neither create nor update.
    # in this case if the model cannot be found then None is returned: (None, False, False)
    return (inst, created, updated)

def ingest(data, create=True, update=True):
    "ingests article-json. returns a triple of (journal obj, article obj, article version obj)"
    context = {}
    try:
        journal_struct = render.render_item(JOURNAL, data['journal'])
        journal, created, updated = \
          create_or_update(models.Journal, journal_struct, ['name'], create, update)
        
        assert isinstance(journal, models.Journal)

        data['article']['journal'] = journal        
        article_struct = render.render_item(ARTICLE, data['article'])
        article, created, updated = \
          create_or_update(models.Article, article_struct, ['msid', 'journal'], create, update)

        assert isinstance(article, models.Article)

        data['article']['article'] = article
        article_version_struct = render.render_item(ARTICLE_VERSION, data['article'])
        article_version, created, update = \
          create_or_update(models.ArticleVersion, article_version_struct, ['article', 'version'], create, update)

        assert isinstance(article_version, models.ArticleVersion)
        
        return journal, article, article_version
    except Exception as err:
        LOG.exception("unhandled exception attempting to ingest article-json", extra=context)
        raise err

def ingest_json(str_json):
    return ingest(json.loads(str_json))
