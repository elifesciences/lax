from django.conf.urls import url
from . import api_v2_views as views

# api_v3_views, if it eventuates, will use the same app-name
# but with a 'v3' namespace in urls.py
appname = "publisher"

urlpatterns = (
    [
        url(r"^articles$", views.article_list, name="article-list"),
        url(r"^articles/(?P<msid>\d+)$", views.article, name="article"),
        url(
            r"^articles/(?P<msid>\d+)/versions$",
            views.article_version_list,
            name="article-version-list",
        ),
        url(
            r"^articles/(?P<msid>\d+)/versions/(?P<version>\d+)$",
            views.article_version,
            name="article-version",
        ),
        url(
            r"^articles/(?P<msid>\d+)/related$",
            views.article_related,
            name="article-relations",
        ),
        # not part of Public API
        # why the odd fragment regex? to support models.XML2JSON 'xml->json' fragment ID
        # simplifying it to alpha-numeric + hyphen may remove a class of problems
        url(
            r"^articles/(?P<msid>\d+)/fragments/(?P<fragment_id>[>\-\w]{3,25})$",
            views.article_fragment,
            name="article-fragment",
        ),
    ],
    appname,
)
