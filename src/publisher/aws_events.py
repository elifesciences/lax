from ordered_set import OrderedSet
import json
from django.conf import settings
import boto3
from publisher import relation_logic as relationships

from multiprocessing import SimpleQueue

import logging

LOG = logging.getLogger(__name__)

def sns_topic_arn():
    "returns an arn path to an AWS event bus. this is used to connect and send/receive events"
    vals = {}
    vals.update(settings.EVENT_BUS)
    # ll: arn:aws:sns:us-east-1:112634557572:bus-articles--ci
    arn = "arn:aws:sns:{region}:{subscriber}:{name}--{env}".format(**vals)
    LOG.info("using topic arn: %s", arn)
    return arn

def event_bus_conn():
    sns = boto3.resource('sns')
    return sns.Topic(sns_topic_arn())

#
#
#

"""
Stores calls to a function to be performed all together as unique calls - i.e. it won't call the function with the same arguments twice.

Using `CallsBatch` limits function arguments to hashable types only.
"""
class CallsBatch:
    def __init__(self, target):
        self.calls = SimpleQueue()
        self.target = target

    def notify(self, *args):
        self.calls.put(args)

    def commit(self):
        unique_calls = OrderedSet()
        original_calls = 0
        while not self.calls.empty():
            # SimpleQueue does not expose its length 
            original_calls = original_calls + 1
            unique_calls.add(self.calls.get())
        LOG.info("%s unique calls to %s to be performed instead of %s", len(unique_calls), self.target, original_calls)
        [self.target(*args) for args in unique_calls]

def notify(msid):
    "notify event bus when this article or one of it's versions has been changed in some way"
    if settings.DEBUG:
        LOG.debug("application is in DEBUG mode, no notifications will be sent")
        return
    try:
        msg = {"type": "article", "id": msid}
        msg_json = json.dumps(msg)
        LOG.debug("writing message to event bus", extra={'bus-message': msg_json})
        event_bus_conn().publish(Message=msg_json)
        return msg_json # used only for testing
    except ValueError as err:
        # probably serializing value
        LOG.error("failed to serialize event bus payload %s", err, extra={'bus-message': msg_json})

    except BaseException as err:
        LOG.exception("unhandled error attempting to notify event bus of article change: %s", err)

BATCH = CallsBatch(notify)

def notify_relations(av):
    "notify event bus of changes to an article version's related articles"
    [BATCH.notify(art.manuscript_id) for art in relationships.internal_relationships_for_article_version(av)]

def notify_all(av):
    BATCH.notify(av.article.manuscript_id)
    notify_relations(av)
