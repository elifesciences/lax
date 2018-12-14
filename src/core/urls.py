from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
import reports.urls

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^explorer/', include('explorer.urls')),

    url(r'^reports/', include(reports.urls)), # deprecated, moving logic to Observer project
    url(r'^', include('publisher.urls')),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
