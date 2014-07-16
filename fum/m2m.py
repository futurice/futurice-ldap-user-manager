from fum.ldap_helpers import ldap_cls, fetch

class Sudoers(object):
    ldap_object_classes = ['top', 'sudoRole']
    ldap_base_dn = "ou=SUDOers,dc=futurice,dc=com"
    ldap_filter = "(objectClass=sudoRole)"
    ldap_attrs = ['sudoUser', 'sudoHost', 'cn']
    ldap_id_field = "cn"

    def get_ldap_record(self, data={}):
        """ Required information on creating this record to LDAP """
        vals = {'cn': self.get_ldap_id_value().encode('ascii'),}
        vals.update(data)
        return [('objectClass', self.ldap_object_classes),
                ('cn', ['{cn}'.format(**vals)]),
                ('description', ['Permissions to use sudo on {cn}'.format(**vals)]),
                ('sudoCommand', ['ALL']),
                ('sudoHost', ['{cn}.futurice.com'.format(**vals)])]

    def __init__(self):
        self.pk = None
        self.ldap = ldap_cls(parent=self)

    def get_ldap_id_value(self):
        return getattr(self, 'name', None)

    def get_dn(self):
        return self.ldap.dn

    def lval(self): # value in LDAP
        return self.ldap.fetch(self.get_dn(), filters=self.ldap_filter, attrs=self.ldap_attrs)
