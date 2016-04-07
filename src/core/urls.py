from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.conf import settings

urlpatterns = [
    url(r'^admin/', include(admin.site.urls))
]
if 'publisher' in settings.INSTALLED_APPS:
    urlpatterns += [
        # integration with upstream api
        url(r'^proxy/lax/api/', include('publisher.api', namespace="proxied")), 
        url(r'^api/', include('publisher.api')),
        url(r'^', include('publisher.urls')),
    ]

if settings.ENV == settings.DEV:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
