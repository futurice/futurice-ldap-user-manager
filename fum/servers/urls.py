from django.conf.urls import patterns, include, url
from views import *

urlpatterns = patterns('',
    url(r'add/$', Create.as_view(), name='%s_add'%NAME),
    url(r'json/$', servers_json, name='%s_json'%NAME),
    url(r'(?P<pk>[ -_\w]+)/users/$', server_detail_json, name='%s_detail'%NAME),
    url(r'(?P<slug>[ -_\w]+)/$', DetailView.as_view(), name='%s_detail'%NAME),
    url(r'^$', ListView.as_view(), name='%s'%NAME),
)
