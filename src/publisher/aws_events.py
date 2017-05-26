import json
from django.conf import settings
import boto3
from publisher import relation_logic as relationships
from publisher.utils import lmap

import logging

LOG = logging.getLogger(__name__)

def sns_topic_arn(**overrides):
    "returns an arn path to an AWS event bus. this is used to connect and send/receive events"
    vals = {}
    vals.update(settings.EVENT_BUS)
    vals.update(overrides)
    # ll: arn:aws:sns:us-east-1:112634557572:bus-articles--ci
    arn = "arn:aws:sns:{region}:{subscriber}:{name}--{env}".format(**vals)
    LOG.info("using topic arn: %s", arn)
    return arn

def event_bus_conn(**overrides):
    sns = boto3.resource('sns')
    return sns.Topic(sns_topic_arn(**overrides))

#
#
#

def notify(art, **overrides):
    "notify event bus when this article or one of it's versions has been changed in some way"
    if settings.DEBUG:
        LOG.debug("application is in DEBUG mode, no notifications will be sent")
        return
    try:
        msg = {"type": "article", "id": art.manuscript_id}
        msg_json = json.dumps(msg)
        LOG.debug("writing message to event bus", extra={'bus-message': msg_json})
        event_bus_conn(**overrides).publish(Message=msg_json)
    except ValueError as err:
        # probably serializing value
        LOG.error("failed to serialize event bus payload %s", err, extra={'bus-message': msg_json})

    except BaseException as err:
        LOG.exception("unhandled error attempting to notify event bus of article change: %s", err)

def notify_relations(av, **overrides):
    "notify event bus of changes to an article version's related articles"
    lmap(notify, relationships.internal_relationships_for_article_version(av))

def notify_all(av, **overrides):
    notify(av.article, **overrides)
    notify_relations(av, **overrides)
