from django.conf.urls import include, url
from . import views, rss
from rest_framework_swagger.views import get_swagger_view

urlpatterns = [
    url(r'^api/docs/', get_swagger_view(title='Article Store API')),
    url(r'^api/v2/', include('publisher.api_v2_urls', namespace='v2')),
    url(r'^rss/articles/', include(rss.urlpatterns)),

    url(r'^$', views.landing, name='pub-landing'),
]
