from django.urls import include, re_path
from django.contrib import admin
from django.conf import settings

urlpatterns = [
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^explorer/", include("explorer.urls")),
    re_path(r"^", include("publisher.urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
