from django.conf.urls import include, url
from . import views, rss

urlpatterns = [
    url(r"^api/v2/", include("publisher.api_v2_urls", namespace="v2")),
    url(r"^rss/articles/", include(rss.urlpatterns)),
    url(r"^$", views.landing, name="pub-landing"),
]
