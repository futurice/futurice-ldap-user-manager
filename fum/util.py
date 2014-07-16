from django.conf import settings
from django.db.models.loading import get_model, get_models
from django.contrib.contenttypes.models import ContentType
import ldap

def append_crud_urls(context, name):
    for k in ['add','update']:
        context['obj_%s'%k] = '%s_%s'%(name,k)

def as_val(k):
    if k is None:
        return k
    if isinstance(k, list):
        k = k[0]
    return int(k)

def get_highlow_id(instance):
    items = instance.ldap.fetch(instance.ldap_base_dn, scope=ldap.SCOPE_ONELEVEL)
    for k in items:
        val = k[1].get(instance.ldap_id_number_field)
        val = as_val(val)
        if val is None or (val<instance.ldap_range[0] or val>instance.ldap_range[-1]):
            print "BAD RANGE! (not in [%s,%s] "%(instance.ldap_range[0], instance.ldap_range[-1])
            print k, val
    items_clean = [as_val(j) for j in [k[1].get(instance.ldap_id_number_field) for k in items] if j]
    items_clean = sorted(items_clean)
    return items, items_clean

project_models = {}
def get_project_models():
    global project_models
    if not project_models:
        project_models = {k().__class__.__name__.lower().rstrip('s'):{'model':k, 'ct': ContentType.objects.get_for_model(k)} for k in get_models() if any(k._meta.app_label in j for j in settings.PROJECT_APPS)}
        #content_type = ContentType.objects.get_for_model(model)
    return project_models
