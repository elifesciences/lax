from django.conf.urls import include, url
import views
import operator

urlpatterns_meta = [
    url(r'docs/', include('rest_framework_swagger.urls')),
]

urlpatterns_v1 = [
    url(r'v1/corpus/info/$', views.corpus_info, name='api-corpus-info'),
    
    url(r'v1/article/create/$', views.create_article, name='api-create-article'),
    url(r'v1/article/update/$', views.update_article, name='api-update-article'),
    url(r'v1/article/create-update/$', views.import_article, name='api-create-update-article'),

    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/attribute/$',  views.add_update_article_attribute, name='api-add-update-article-attribute'),
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/attribute/(?P<attribute>[\-\w]+)/$',  views.get_article_attribute, name='api-get-article-attribute'),

    # all versions of an article
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/version/$', views.get_article_versions, name='api-article-versions'),

    # specific version of a specific article
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/version/(?P<version>\d{0,3})/$', views.get_article, name='api-article-version'),

    # latest version of a specific article
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.get_article, name='api-article'),
]

urlpatterns_v2 = [
    # ...
]

urlpatterns = reduce(operator.add, [urlpatterns_meta, urlpatterns_v1, urlpatterns_v2])
