from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.template import add_to_builtins
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^v1/', include('fum.api.urls')),
    url(r'^', include('fum.api.urls')),
    url(r'^rest-api/', include('rest_framework_docs.urls')),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

add_to_builtins('fum.common.templatetags.tags')
