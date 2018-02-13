from django.conf.urls import url
from . import api_v2_views as views

urlpatterns = [
    url(r'^ping$', views.ping, name='ping'),
    url(r'^articles$', views.article_list, name='article-list'),
    url(r'^articles/(?P<msid>\d+)$', views.article, name='article'),
    url(r'^articles/(?P<msid>\d+)/versions$', views.article_version_list, name='article-version-list'),
    url(r'^articles/(?P<msid>\d+)/versions/(?P<version>\d+)$', views.article_version, name='article-version'),
    url(r'^articles/(?P<msid>\d+)/related$', views.article_related, name='article-relations'),

    # not part of Public API
    url(r'^articles/(?P<msid>\d+)/fragments/(?P<fragment_id>[>\-\w]{3,25})$', views.article_fragment, name='article-fragment'),
]
