from django.conf.urls import include, url
import views
import operator

urlpatterns_v1 = [
    url(r'v1/docs/$', include('rest_framework_swagger.urls')),
    url(r'v1/import/article/$', views.import_article, name='api-import-article'),
    
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/attribute/$',  views.article_attribute, name='api-article-attribute'),
    url(r'v1/article/(?P<doi>[\.\w]+\/[\.\w]+)/$', views.get_article, name='api-article'),
]

urlpatterns_v2 = [
    # ...
]

urlpatterns = reduce(operator.add, [urlpatterns_v1, urlpatterns_v2])
