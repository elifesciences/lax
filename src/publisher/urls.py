from django.conf.urls import include, url
import views, rss, reports_urls

urlpatterns = [
    url(r'^api/v2/', include('publisher.api_v2_urls')),
    url(r'^api/v1/', include('publisher.api_v1_urls')),
    url(r'^rss/articles/', include(rss.urlpatterns)),
    url(r'^reports/', include(reports_urls.urlpatterns)),
    
    url(r'^$', views.landing, name='pub-landing'),
]
