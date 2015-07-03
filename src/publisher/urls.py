from django.conf.urls import patterns, include, url
from django.contrib import admin

import views

urlpatterns = [
    url(r'^$', views.landing, name='pub-landing'),
    url(r'article-list/$', views.article_list, name='article-list'),

]

# API pending Swagger or something sexier
urlpatterns += [
    url(r'import-article/$', views.import_article, name='import-article'),
    url(r'add-attribute-to-article/(?P<doi>[\.\w]+\/[\.\w]+)/(?P<version>\d{0,1})/$',  views.add_attribute, name='add-attribute-to-article'),

]
