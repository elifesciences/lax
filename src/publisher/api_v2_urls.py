from django.conf.urls import include, url
import api_v2_views as views

urlpatterns = [
    url(r'articles$', views.article_list, name='article-list'),
    url(r'articles/(?P<id>\w+)$', views.article, name='article'),
    url(r'articles/(?P<id>\w+)/versions$', views.article_version_list, name='article-version-list'),
    url(r'articles/(?P<id>\w+)/versions/(?P<version>\d+)$', views.article_version, name='article-version'),
]
