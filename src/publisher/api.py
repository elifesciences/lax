from django.conf.urls import include, url
import views
import operator

urlpatterns_v1 = [
    url(r'v1/import-article/$', views.import_article, name='import-article'),
    url(r'v1/add-attribute-to-article/(?P<doi>[\.\w]+\/[\.\w]+)/$',  views.add_attribute, name='add-attribute-to-article'),
]

urlpatterns_v2 = [
    # ...
]

urlpatterns = reduce(operator.add, [urlpatterns_v1, urlpatterns_v2])
