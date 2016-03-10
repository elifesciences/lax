from django.conf.urls import include, url
import views, rss

urlpatterns = [
    url(r'^rss/articles/', include(rss.urls)),
    url(r'^$', views.landing, name='pub-landing'),
]
