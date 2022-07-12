from django.urls import re_path
from . import api_v2_views as views

# api_v3_views, if it eventuates, will use the same app-name
# but with a 'v3' namespace in urls.py
appname = "publisher"

urlpatterns = (
    [
        re_path(r"^articles$", views.article_list, name="article-list"),
        re_path(r"^articles/(?P<msid>\d+)$", views.article, name="article"),
        re_path(
            r"^articles/(?P<msid>\d+)/versions$",
            views.article_version_list,
            name="article-version-list",
        ),
        re_path(
            r"^articles/(?P<msid>\d+)/versions/(?P<version>\d+)$",
            views.article_version,
            name="article-version",
        ),
        re_path(
            r"^articles/(?P<msid>\d+)/related$",
            views.article_related,
            name="article-relations",
        ),
        # not part of Public API
        # why the odd fragment regex? to support models.XML2JSON 'xml->json' fragment ID
        # simplifying it to alpha-numeric + hyphen may remove a class of problems
        re_path(
            r"^articles/(?P<msid>\d+)/fragments/(?P<fragment_id>[>\-\w]{3,25})$",
            views.article_fragment,
            name="article-fragment",
        ),
    ],
    appname,
)
