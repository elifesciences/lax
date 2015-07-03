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

]
