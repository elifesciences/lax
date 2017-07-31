from ordered_set import OrderedSet
import json
from django.conf import settings
import boto3
from publisher import relation_logic as relationships
from functools import wraps

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

SAFEWORD = 'cacao'

def defer(fn):
    """calls function normally until safeword is received then buffers all requests until the safeword is called again.
    when the safeword is received a second time, the wrapped function is called with the UNIQUE set of arguments - i.e. it won't be called with the same arguments twice.

    using `defer` limits function arguments to hashable types only.

    """

    call_queue = SimpleQueue()
    deferring = False

    @wraps(fn)
    def wrapper(*args):
        arg = args[0]
        nonlocal deferring # stateful!

        if arg == SAFEWORD:
            deferring = not deferring
            if deferring:
                # nothing else to do this turn
                return

            # we're not deferring and we have stored calls to process
            if not call_queue.empty():
                # input order cannot be guaranteed as we're using multiprocessing
                # single-process input order can be guaranteed
                calls = OrderedSet()
                while not call_queue.empty():
                    calls.add(call_queue.get())
                return [fn(*fnargs) for fnargs in calls]

            else:
                # we're not deferring and we have no calls to process
                # TODO: empty list or None ?
                return

        # store the args if we're deferring and return
        if deferring:
            call_queue.put(args)
            return

        # we're not deferring, call wrapped fn as normal
        return fn(*args)
    return wrapper


#
#
#

@defer
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

def notify_relations(av):
    "notify event bus of changes to an article version's related articles"
    [notify(art.manuscript_id) for art in relationships.internal_relationships_for_article_version(av)]

def notify_all(av):
    notify(av.article.manuscript_id)
    notify_relations(av)
