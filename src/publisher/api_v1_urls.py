from django.conf.urls import url
import api_v1_views as views

urlpatterns = [
    url(r'corpus/info/$', views.corpus_info, name='api-corpus-info'),

    url(r'article/create/$', views.create_article, name='api-create-article'),
    url(r'article/update/$', views.update_article, name='api-update-article'),
    url(r'article/create-update/$', views.import_article, name='api-create-update-article'),

    # all versions of an article
    url(r'article/(?P<doi>[\.\w]+\/[\.\w]+)/version/$', views.get_article_versions, name='api-article-versions'),

    # specific version of a specific article
    url(r'article/(?P<doi>[\.\w]+\/[\.\w]+)/version/(?P<version>\d{0,3})/$', views.get_article, name='api-article-version'),

    # latest version of a specific article
    url(r'article/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.get_article, name='api-article'),
]
