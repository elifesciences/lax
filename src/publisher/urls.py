from django.conf.urls import include, url
import views, rss

urlpatterns = [
    url(r'^api/v2/', include('publisher.api_v2_urls')),
    url(r'^api/v1/', include('publisher.api_v1_urls')),
    url(r'^rss/articles/', include(rss.urlpatterns)),

    
    url(r'^$', views.landing, name='pub-landing'),
]
