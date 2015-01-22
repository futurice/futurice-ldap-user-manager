from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.template import add_to_builtins
from django.contrib import admin
admin.autodiscover()

from views import IndexView

urlpatterns = patterns('',
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'^', include('fum.common.urls')),
    url(r'^users/', include('fum.users.urls')),
    url(r'^groups/', include('fum.groups.urls')),
    url(r'^servers/', include('fum.servers.urls')),
    url(r'^projects/', include('fum.projects.urls')),
    url(r'^api/', include('fum.api.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^rest-api/', include('rest_framework_docs.urls')),
    url(r'^hsearch/', include('haystack.urls')),
    url(r'^history/', include('djangohistory.urls')),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

add_to_builtins('fum.common.templatetags.tags')
