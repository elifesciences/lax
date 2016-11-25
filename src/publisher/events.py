import json
from django.conf import settings
import boto3

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

#
#
#

def event_bus_conn(**overrides):
    sns = boto3.resource('sns')
    return sns.Topic(sns_topic_arn(**overrides))

'''
# works, but no tests
import uuid
def _create_queue():
    sqs = boto3.resource('sqs')
    queue_name = "lax-temp-listener-" + str(uuid.uuid4())
    LOG.info("attempting to create queue %r", queue_name)
    return sqs.create_queue(QueueName=queue_name)

def get_message(queue):
    messages = []
    while not messages:
        messages = queue.receive_messages(
            MaxNumberOfMessages=1,
            VisibilityTimeout=60, # time allowed to call delete, can be increased
            WaitTimeSeconds=20 # maximum setting for long polling
        )
    message = messages[0]
    return message

def listen(env):
    "creates a temporary queue and subscription to topic (event bus) for given region. destroyed afterwards"
    queue = subscription = perm_label = None
    try:
        topic = event_bus_conn(env=env)
        queue = _create_queue()
        queue_arn = queue.attributes['QueueArn']
        _bits = queue_arn.split(':')
        acc_id, qname = _bits[4], _bits[5]

        # queue can receive messages from topic
        # this attaches a Policy to the queue that we can modify
        queue.add_permission(**{
            'Label': 'perm-%s-to-sns' % qname,
            'AWSAccountIds': [acc_id],
            'Actions': [
                '*',
            ]
        })

        # policy ll:
        # {"Version":"2008-10-17","Id":"arn:aws:sqs:us-east-1:512686554592:lax-temp-listener-b37e2179-3b83-4c00-853d-ee541893ce8e/SQSDefaultPolicy","Statement":[{"Sid":"perm-lax-temp-listener-b37e2179-3b83-4c00-853d-ee541893ce8e-to-sns","Effect":"Allow","Principal":{"AWS":"arn:aws:iam::512686554592:root"},"Action":"SQS:*","Resource":"arn:aws:sqs:us-east-1:512686554592:lax-temp-listener-b37e2179-3b83-4c00-853d-ee541893ce8e"}]}
        policy = json.loads(queue.attributes['Policy'])
        policy['Statement'][0]["Principal"] = {"AWS": "*"}
        queue.set_attributes(Attributes={'Policy': json.dumps(policy)})

        # topic allows subscription
        perm_label = 'perm-for-%s' % qname
        topic.add_permission(**{
            'Label': perm_label,
            'AWSAccountId': [acc_id],
            'ActionName': [
                'subscribe',
                'receive',
                'publish'
            ]})

        subscription = topic.subscribe(Protocol='sqs', Endpoint=queue_arn)

        message = get_message(queue)
        print 'message:', message

        body = json.loads(message.body)
        print 'message body:', body

        body_message = json.loads(body['Message'])
        print 'message body decoded:', body_message

    except KeyboardInterrupt:
        pass

    finally:
        # destroy subscription
        # destroy queue
        LOG.info("deleting queue")
        if queue:
            queue.delete()

        if subscription:
            subscription.delete()

        if perm_label:
            topic.remove_permission(Label=perm_label)
'''

def notify(art, **overrides):
    "notify the event bus when this article or one of it's versions has been changed in some way"
    if settings.DEBUG:
        LOG.debug("application is in DEBUG mode, not notifying anyone")
        return
    try:
        msg = {"type": "article", "id": art.manuscript_id}
        #msg_json = json.dumps({'default': msg})
        msg_json = json.dumps(msg)
        LOG.debug("writing message to event bus", extra={'bus-message': msg_json})
        event_bus_conn(**overrides).publish(Message=msg_json)  # , MessageStructure='json')
    except ValueError as err:
        # probably serializing value
        LOG.error("failed to serialize event bus payload %s", err, extra={'bus-message': msg_json})

    except Exception as err:
        LOG.error("unhandled error attempting to notify event bus of article change: %s", err)
