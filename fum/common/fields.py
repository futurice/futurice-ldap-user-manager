from django.conf import settings
from django.db import models

from fum.ldap_helpers import fetch

class LdapManyToManyField(models.ManyToManyField):
    is_local = True # ldap_field is stored in parent Table?

    def ldap_attrs(self):
        tmp = []
        for k,v in self.ldap_fields.iteritems():
            if isinstance(v, list):
                tmp += v
            else:
                tmp.append(v)
        return tmp

    def lval(self, parent, extra_attrs=[]): # value in LDAP
        attrs = list(set(parent.ldap_attrs()+extra_attrs))
        return parent.ldap.fetch(self.get_dn(parent=parent, child=None), filters=parent.ldap_filter, attrs=attrs)

class UsersManyField(LdapManyToManyField):
    ldap_field = 'uniqueMember'

    def get_m2m_cls(self):
        from ..models import Users
        return Users

    def get_dn(self, parent, child):
        return parent.get_dn()

    def as_value(self, parent, child):
        return ("uid=%s,%s" % (child.get_ldap_id_value(), child.ldap_base_dn)).encode('utf-8')

class SudoersManyField(LdapManyToManyField):
    ldap_base_dn = settings.SUDO_DN
    ldap_field = 'sudoUser'
    ldap_fields = {
            'a': 'sudoUser',
            'b': 'sudoHost',
            'c': 'cn'}
    is_local = False

    def get_m2m_cls(self):
        from ..m2m import Sudoers
        return Sudoers

    def get_dn(self, parent, child):
        return 'cn=%s,%s' % (parent.get_ldap_id_value(), self.ldap_base_dn)

    def as_value(self, parent, child):
        return (child.get_ldap_id_value()).encode('utf-8')

    def lval(self, parent, extra_attrs=[]): # value in LDAP
        attrs = list(set(self.ldap_attrs()+extra_attrs))
        return parent.ldap.fetch(self.get_dn(parent=parent, child=None), filters=parent.ldap_filter, attrs=attrs)


from south.modelsinspector import add_introspection_rules
add_introspection_rules([], ['^fum\.common\.fields\.UsersManyField'])
add_introspection_rules([], ['^fum\.common\.fields\.SudoersManyField'])
