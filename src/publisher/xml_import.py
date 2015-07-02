import os
import models, utils
from core import utils as core_utils
from elifetools import parseJATS as parser
from django.conf import settings

import logging

logger = logging.getLogger(__name__)

def import_article_from_xml(path_to_xml):
    "'imports' an article into the pppp system"

    path_to_xml = os.path.abspath(path_to_xml)
    
    if not core_utils.is_xml(path_to_xml):
        raise ValueError("File doesn't appear to be XML. XML files have a '.xml' extension and can be read by the xml parser. I got: %s" % path_to_xml)

    soup = parser.parse_document(path_to_xml)
    obj, new = models.Article.objects.update_or_create(**{
        'journal': journal(),
        'doi': parser.doi(soup),    
        'defaults': {'title': parser.title(soup)},
    })

    if new:
        logging.info("created new Article %r" % obj)
    else:
        logging.info("updated Article %r" % obj)
        
    return obj
