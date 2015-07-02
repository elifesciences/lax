import os
import models, utils
from django.conf import settings

import logging
logger = logging.getLogger(__name__)

def journal(journal_name=settings.PRIMARY_JOURNAL):
    obj, new = models.Journal.objects.get_or_create(name=journal_name)
    if new:
        logger.info("created new Journal %s" % obj)
    return obj
