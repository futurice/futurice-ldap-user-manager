from django.conf.urls import url, patterns, include
from django.contrib.auth.models import User, Group
from rest_framework import viewsets, routers
from rest_framework.routers import DefaultRouter
import views

router = DefaultRouter()
router.register(r'users', views.UsersViewSet)
router.register(r'groups', views.GroupsViewSet)
router.register(r'servers', views.ServersViewSet)
router.register(r'projects', views.ProjectsViewSet)
router.register(r'emails', views.EMailsViewSet)
router.register(r'aliases', views.EMailAliasesViewSet)

# rest-framework serializers are not done yet; refactor mod_* code to get routings done by the framework
router_urls = router.get_urls()
related_urls = []
patch_support_for_relations = ['users','resources','aliases','sudoers','projects','groups']
def add_related_patterns():
    for p in patch_support_for_relations:
        for k in router.get_urls():
            if '-%s'%p in k.name and 'format' not in k.__dict__['_regex']:
                rgz = r'%s(?P<relname>[^/]+)/$'%k.__dict__['_regex'].rstrip('$')
                new_route = url(rgz, k.callback, name=u'%s-related'%k.name)
                related_urls.append(new_route)
add_related_patterns()
router_urls += related_urls

urlpatterns = patterns('',
    url(r'^', include(router_urls)),
    url(r'^photo/(?P<username>\w+)/(?P<size>\w+)?', views.userphoto, name='api-user-photo'),
    url(r'^list/employees/', views.list_employees, name='api-list-employees'),
)

