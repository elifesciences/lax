from django.conf.urls import include, url
import views, rss

urlpatterns = [
    url(r'^api/docs/', include('rest_framework_swagger.urls')),
    url(r'^api/v2/', include('publisher.api_v2_urls', namespace='v2')),
    url(r'^api/v1/', include('publisher.api_v1_urls')),
    url(r'^rss/articles/', include(rss.urlpatterns)),

    url(r'^$', views.landing, name='pub-landing'),
]
