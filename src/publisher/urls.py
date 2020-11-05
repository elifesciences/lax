from django.conf.urls import include, url
from . import views, api_v2_urls

urlpatterns = [
    url(r"^api/v2/", include(api_v2_urls.urlpatterns, namespace="v2")),
    url(r"^$", views.landing, name="pub-landing"),
]
