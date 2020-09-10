from django.conf.urls import include, url
from . import views, rss, api_v2_urls

urlpatterns = [
    url(r"^api/v2/", include(api_v2_urls.urlpatterns, namespace="v2")),
    url(r"^rss/articles/", include(rss.urlpatterns)),
    url(r"^$", views.landing, name="pub-landing"),
]
