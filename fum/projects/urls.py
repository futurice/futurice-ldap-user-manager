from django.conf.urls import patterns, include, url
from views import *

urlpatterns = patterns('',
    url(r'add/$', Create.as_view(), name='%s_add'%NAME),
    url(r'json/$', projects_json, name='%s_json'%NAME),
    url(r'(?P<projectname>[ -_\w]+)/users/$', projects_detail_json, name='%s_detail'%NAME),
    url(r'(?P<slug>[ -_\w]+)/$', DetailView.as_view(), name='%s_detail'%NAME),
    url(r'^$', ListView.as_view(), name='%s'%NAME),
)
