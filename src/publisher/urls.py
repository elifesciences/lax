from django.conf.urls import include, url
import views

urlpatterns = [
    url(r'^$', views.landing, name='pub-landing'),
    url(r'article-list/$', views.article_list, name='article-list'),
]
