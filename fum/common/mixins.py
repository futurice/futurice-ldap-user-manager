from djangodirtyfield.mixin import TypedDirtyFieldMixin

class DirtyFieldsMixin(TypedDirtyFieldMixin):
    sources = {'default': {'state': '_original_state', 'lookup': '_as_dict', 'fields': 'get_fields'},
            'ldap': {'state': '_ldap_original_state', 'lookup': '_ldap_as_dict', 'fields': 'get_ldap_fields'}}
    def _ldap_as_dict(self, *args, **kwargs):
        fields = {}
        for k,v in getattr(self, 'ldap_only_fields', {}).iteritems():
            fields.update({k: getattr(self, k, '')})
        return fields

    def get_ldap_fields(self):
        return self.ldap_only_fields.keys()
