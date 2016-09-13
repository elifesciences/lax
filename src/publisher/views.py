from os.path import join
import os
from django.conf import settings
from annoying.decorators import render_to

import logging
LOG = logging.getLogger(__name__)

@render_to("publisher/landing.html")
def landing(request):
    project_root = os.path.abspath(join(settings.SRC_DIR, '..'))
    return {
        'readme': open(join(project_root, 'README.md')).read()
    }
