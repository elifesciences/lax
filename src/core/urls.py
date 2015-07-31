from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^docs/', include('rest_framework_swagger.urls')),
    url(r'^api/', include('publisher.api')),
    url(r'^', include('publisher.urls')),
]

if settings.ENV == settings.DEV:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
