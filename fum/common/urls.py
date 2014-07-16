from django.conf.urls import patterns, include, url
from views import *

urlpatterns = patterns('',
    url(r'^search/$', SearchView.as_view(), name='searchall'),
    url(r'^sudo/logout/$', end_superuser, name='end_superuser'),
    url(r'^sudo/$', enable_superuser, name='enable_superuser'),
    url(r'^audit/$', AuditView.as_view(), name='audit'),
)
