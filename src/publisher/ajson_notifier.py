import json
import boto3
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete
from django.conf import settings
from . import models

import logging
LOG = logging.getLogger(__name__)

#@cache # ?
def conn():
    sqs = boto3.resource('sqs')
    queue = sqs.get_queue_by_name(QueueName=settings.BUS_QUEUE_NAME)
    return queue

@receiver(post_save, sender=models.ArticleVersion)
@receiver(pre_delete, sender=models.ArticleVersion)
def notify_event_bus(sender, instance, **rest):    
    msg = {"type": "article", "id": instance.article.manuscript_id}
    msg_json = json.dumps(msg)
    if settings.DEBUG:
        LOG.debug(msg_json)
    else:
        conn().write(msg_json)
