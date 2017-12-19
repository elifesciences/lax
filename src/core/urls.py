from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from graphene_django.views import GraphQLView

from core.schema import schema
import reports.urls


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^explorer/', include('explorer.urls')),

    url(r'^reports/', include(reports.urls)), # deprecated, moving logic to Observer project
    url(r'^', include('publisher.urls')),
]

if settings.GRAPHQL_ENABLED:
    urlpatterns += [
        url(r'^graphql', GraphQLView.as_view(graphiql=True, schema=schema)),
    ]

if settings.ENV == settings.DEV:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
