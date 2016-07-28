from django.conf.urls import include, url
import views

#
#
#

urlpatterns = [
    url(r'^paw/ahead.xml$', views.PAWAheadReport(), name='paw-ahead-report'),
    url(r'^paw/recent.xml$', views.PAWRecentReport(), name='paw-recent-report'),
    # these are more for testing but can be used to generate very large rss feeds
    url(r'^paw/(?P<days_ago>\d{1,4})/ahead.xml$', views.PAWAheadReport(), name='paw-ahead-report'),
    url(r'^paw/(?P<days_ago>\d{1,4})/recent.xml$', views.PAWRecentReport(), name='paw-recent-report'),
    url(r'^published.csv$', views.article_poa_vor_pubdates, name='poa-vor-pubdates'),
    url(r'^time-to-publication.csv$', views.time_to_publication, name='time-to-publication'),
]
