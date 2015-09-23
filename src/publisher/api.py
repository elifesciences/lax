from django.conf.urls import include, url
import views
import operator

urlpatterns_meta = [
    url(r'docs/', include('rest_framework_swagger.urls')),
]

urlpatterns_v1 = [
    url(r'v1/corpus/info/$', views.corpus_info, name='api-corpus-info'),
    
    url(r'v1/import/article/$', views.import_article, name='api-import-article'),
    
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/attribute/$',  views.add_update_article_attribute, name='api-add-update-article-attribute'),
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/attribute/(?P<attribute>[\-\w]+)/$',  views.get_article_attribute, name='api-get-article-attribute'),

    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/version/$', views.get_article_versions, name='api-article-versions'),
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/version/(?P<version>\d+)/$', views.get_article, name='api-article'),
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.get_article, name='api-article'),
]

urlpatterns_v2 = [
    # ...
]

urlpatterns = reduce(operator.add, [urlpatterns_meta, urlpatterns_v1, urlpatterns_v2])
