from django.conf.urls import include, url
import api_v2_views as views

urlpatterns = [
    url(r'article$', views.article),
    

]
