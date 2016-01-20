from django.conf.urls import include, url
import views

urlpatterns = [
    url(r'^$', views.landing, name='pub-landing'),
]
