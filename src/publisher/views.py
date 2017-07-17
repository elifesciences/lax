import os
from django.conf import settings
from annoying.decorators import render_to

@render_to("publisher/landing.html")
def landing(request):
    project_root = os.path.abspath(os.path.join(settings.SRC_DIR, '..'))
    return {
        'readme': open(os.path.join(project_root, 'README.md')).read()
    }
