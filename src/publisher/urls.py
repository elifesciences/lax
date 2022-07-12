from django.urls import include, re_path
from . import views, api_v2_urls

urlpatterns = [
    re_path(r"^api/v2/", include(api_v2_urls.urlpatterns, namespace="v2")),
    re_path(r"^$", views.landing, name="pub-landing"),
]
