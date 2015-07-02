from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns('publisher.views',
    url(r'^$', 'landing', name='pub-landing'),
    url(r'article-list/$', 'article_list', name='article-list'),
)
