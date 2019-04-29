import json
from dateutil import parser
from . import models, utils, events
from django.db import transaction

import logging

LOG = logging.getLogger(__name__)


def import_article(journal, article_data, create=True, update=False):
    article_data["journal"] = journal
    msid = article_data["manuscript_id"]
    article_data["doi"] = utils.msid2doi(msid)

    try:
        art, created, updated = utils.create_or_update(
            models.Article, article_data, ["manuscript_id", "journal"], create, update
        )
        if created or updated:
            LOG.info("%s Article %s", "created" if created else "updated", art)

        # no point creating events if nothing to be preserved
        if create or update:
            events.ejp_ingest_events(art, article_data)

        return art, created, updated

    except Exception as err:
        LOG.exception(
            "unhandled error (%s) attempting to import article from EJP: %s",
            err,
            article_data,
        )
        raise


#
#
#

# http://stackoverflow.com/questions/14995743/how-to-deserialize-the-datetime-in-a-json-object-in-python
def load_with_datetime(pairs):  # , format='%Y-%m-%d'):
    """Load with dates"""
    d = {}
    for k, v in pairs:
        if isinstance(v, str):
            if k.startswith("date_"):
                v = parser.parse(v)
        d[k] = v
    return d


def import_article_list_from_json_path(journal, json_path, *args, **kwargs):
    with open(json_path, "r") as fh:
        article_list = json.load(fh, object_pairs_hook=load_with_datetime)
    with transaction.atomic():

        def fn(ad):
            try:
                return import_article(journal, ad, *args, **kwargs)
            except AssertionError as e:
                LOG.error(
                    "failed to import article with msid %r: %s", ad["manuscript_id"], e
                )
                LOG.error("full data %s", ad)
                raise

        utils.lmap(fn, article_list)
