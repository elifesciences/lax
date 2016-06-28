from django.conf.urls import include, url
import views, rss

urlpatterns = [
    url(r'^rss/articles/', include(rss.urls)),

    url(r'^reports/paw/ahead.xml$', views.PAWAheadReport(), name='paw-ahead-report'),
    url(r'^reports/paw/recent.xml$', views.PAWRecentReport(), name='paw-recent-report'),

    url(r'^reports/published.csv$', views.article_poa_vor_pubdates, name='poa-vor-pubdates'),
    url(r'^reports/time-to-publication.csv$', views.time_to_publication, name='time-to-publication'),
    url(r'^$', views.landing, name='pub-landing'),
]
