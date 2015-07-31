from django.conf.urls import include, url
import views
import operator

urlpatterns_meta = [
    url(r'docs/', include('rest_framework_swagger.urls')),
]

urlpatterns_v1 = [
    url(r'v1/import/article/$', views.import_article, name='api-import-article'),
    
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/attribute/$',  views.add_article_attribute, name='api-add-article-attribute'),
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/attribute/(?P<attribute>[\-\w]+)/$',  views.get_article_attribute, name='api-get-article-attribute'),
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.get_article, name='api-article'),
]

urlpatterns_v2 = [
    # ...
]

urlpatterns = reduce(operator.add, [urlpatterns_meta, urlpatterns_v1, urlpatterns_v2])
