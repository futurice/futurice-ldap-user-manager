#encoding=utf8
from django.db import models
from django.conf import settings
from django.utils.dateformat import format
from django.core.exceptions import ObjectDoesNotExist

import logging, json, time, copy
import ldap
from ldap import modlist
from datetime import datetime
from pprint import pprint as pp

from fum.common.util import to_json, ldap_log
from ldappool import ConnectionManager

log = logging.getLogger(__name__)

TOTAL_CONNECTIONS = 0
cm = ConnectionManager(
        uri=settings.LDAP_CONNECTION.get('uri'),
        use_tls=settings.USE_TLS,
        )

def open_ldap(bind_dn=None, bind_pwd=None):
    return LDAPBridge(parent=None, BIND_DN=bind_dn, BIND_PASSWORD=bind_pwd)

def fetch(self, dn, filters='', attrs=[], scope=ldap.SCOPE_BASE, connection=None):
    specials = []
    normals = []
    for a in attrs:
        if isinstance(a, tuple):
            specials.append(a)
        else:
            normals.append(a)

    result = connection.search_s(dn, scope, filters, normals)[0][1]

    for s in specials:
        res = connection.search_s('cn=%s,%s'%(result['cn'],s[0]), scope, filters, [s[1]])
        if len(res) > 0:
            result[s[1]] = res[0][1][s[1]+"s"]
        else:
            result[s[1]] = []

    return result

def test_user_ldap(username, password, connection=None):
    '''
    Test that user has access to ldap with given credentials.
    Returns true or false
    '''
    from fum.models import Users
    if len(username)>0 and len(password)>0:
        user = Users.objects.get(username=username)
        try:
            if connection is None:
                user.ldap._connection = LDAPBridge(parent=user, BIND_DN=user.get_dn(), BIND_PASSWORD=password).connection
            else:
                user.ldap._connection = connection
            return True
        except Exception, e:
            print "ERROR#helpers: %s, %s"%(username,e)
    return False

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

class LDAPBridge(object):
    """ In LDAP there are Users, Groups, Servers, Projects. Users can be part of the others as uniqueMember MultiValueFields. """

    def __init__(self, parent, dn=None, **kwargs):
        """
        The class is instantiated with the parent object (DN) that we want to work against in LDAP
        """
        self._connection = None
        self._connection_bound = False
        self.settings = AttrDict()
        self.settings.uri = kwargs.get('uri', settings.LDAP_CONNECTION.get('uri'))
        self.settings.START_TLS = True
        self.settings.CONNECTION_OPTIONS = kwargs.get('LDAP_CONNECTION_OPTIONS', None) or settings.LDAP_CONNECTION_OPTIONS
        self.settings.BIND_DN = kwargs.get('BIND_DN', None) or settings.LDAP_CONNECTION.get('bind_dn')
        self.settings.BIND_PASSWORD = kwargs.get('BIND_PASSWORD', None) or settings.LDAP_CONNECTION.get('bind_pwd')
        self.ldap = ldap

        self.parent_instance = parent

        self.dn = None

        self.creating = False
        if self.parent_instance:
            self.creating = False if self.parent_instance.pk else True
            self.dn = self.parent_instance.get_dn()

    def fetch(self, dn, filters='(objectClass=*)', attrs=None, scope=ldap.SCOPE_BASE):
        result = self.op_search(dn, scope, filters, attrs)
        if scope == ldap.SCOPE_BASE:
            return result[0][1]
        return result

    #
    # LDAP connection
    #
    def _bind(self):
        self._bind_as(self.settings.BIND_DN,
            self.settings.BIND_PASSWORD,
            sticky=True)

    def _bind_as(self, bind_dn, bind_password, sticky=False, retry_number=0):
        try:
            self._get_connection().simple_bind_s(bind_dn.encode('utf-8'), bind_password.encode('utf-8'))
        except ldap.SERVER_DOWN, e:
            if retry_number == 0:
                self._connection = None
                return self._bind_as(bind_dn=bind_dn, bind_password=bind_password, sticky=sticky, retry_number=1)

        self._connection_bound = sticky

    def _get_connection(self):
        global TOTAL_CONNECTIONS
        if self._connection is None:
            TOTAL_CONNECTIONS += 1
            log.debug("Opening LDAP connection (%s) [%s/%s] :: %s"%(self.settings.uri,
                self.settings.BIND_DN,
                self.settings.BIND_PASSWORD[:2]+'****',
                TOTAL_CONNECTIONS))
            self._connection = self.ldap.initialize(
                    uri=self.settings.uri,
                    trace_level=settings.LDAP_TRACE_LEVEL)

            for opt, value in self.settings.CONNECTION_OPTIONS.iteritems():
                self._connection.set_option(opt, value)

            if self.settings.START_TLS:
                ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, 0)
                self._connection = self.ldap.initialize(self.settings.uri, trace_level=settings.LDAP_TRACE_LEVEL)
                self._connection.start_tls_s()

        return self._connection

    def _get_bound_connection(self):
        if not self._connection_bound:
            self._bind()
        return self._get_connection()
    connection = property(_get_bound_connection)

    def get_modify_modlist(self, values, force_update=False):
        """ Current values are always empty, requiring extra hand-holding for empty values.
        @TODO pass existing values """
        current_values = {}
        mlist = modlist.modifyModlist(current_values, values)
        mlist_keys = [k[1] for k in mlist]
        for k, m in enumerate(values.keys()):
            if m not in mlist_keys:
                mlist.append((ldap.MOD_DELETE, m, None))
        for k, m in enumerate(mlist):
            mlist[k] = (ldap.MOD_REPLACE, mlist[k][1], mlist[k][2])
        return mlist

    def get_add_modlist(self, values):
        return modlist.addModlist(values)

    def needs_saving(self, modified_values={}):
        return (self.creating or len(modified_values) > 0)

    #
    # LDAP operations abstraction
    #
    #

    def op_add(self, dn, mlist):
        self.connection.add_s(dn, mlist)

    def op_modify(self, dn, mlist):
        self.connection.modify_s(dn, mlist)

    def op_modify_ext(self, dn, mlist):
        self.connection.modify_ext_s(dn, mlist)

    def op_delete(self, dn):
        return self.connection.delete_s(dn)

    def op_search(self, dn, scope, filters, attrs):
        return self.connection.search_s(dn, scope, filters, attrs)

    #
    #
    #
    #

    def create(self, dn=None, values={}, extra={}):
        modified_values = self.model_fields_to_ldap_fields(values, extra, mode='create')
        mlist = self.get_add_modlist(modified_values)
        if not self.needs_saving(modified_values):
            log.debug("LDAP: No create required: %s"%self.dn)
            return
        log.debug("LDAP.create %s :: %s"%(self.dn, ldap_log(mlist)))
        # TODO: check for duplicates in objectClass
        if dn:
            create_dn=dn
        elif self.dn:
            create_dn=dn
        else:
            raise Exception("No DN specified, unable to save to LDAP.")
        self.op_add(create_dn, mlist)

    def save(self, values={}, extra={}, **kwargs):
        modified_values = self.model_fields_to_ldap_fields(values, extra, mode='save')
        self.kwargs = kwargs
        force_update = kwargs.get('force_update', False)
        mlist = self.get_modify_modlist(modified_values, force_update=force_update)
        if not self.needs_saving(modified_values):
            log.debug("LDAP: No save required: %s"%self.dn)
            return
        if mlist:
            log.debug("LDAP.save %s :: %s"%(self.dn, ldap_log(mlist)))
            self.op_modify(self.dn, mlist)

    def delete(self, dn=None):
        dn = dn or self.dn
        log.debug("LDAP.delete %s"%(dn))
        return self.op_delete(dn)

    def create_raw(self, dn, mlist):
        log.debug("LDAP.create_raw %s"%dn)
        self.op_add(dn, mlist)

    def save_raw(self, dn, mlist):
        log.debug("LDAP.save_raw %s"%dn)
        self.op_modify(dn, mlist)

    def save_ext_raw(self, dn, mlist):
        log.debug("LDAP.save_ext_raw %s"%dn)
        self.op_modify_ext(dn, mlist)

    #
    #
    # ManyToMany relations
    #
    #

    def save_relation(self, parent, child, field):
        """ a relation, represented as DN, exists or it does not, it is not modified in-place """
        dn = field.get_dn(parent, child)
        values = self.prepare_related_values(parent, child, field)

        mlist = [(ldap.MOD_ADD, field.ldap_field, values)]
        log.debug("LDAP.save_relation %s :: %s"%(dn, ldap_log(mlist)))
        self.op_modify_ext(dn, mlist)

    def delete_relation(self, parent, child, field):
        dn = field.get_dn(parent, child)
        values = self.prepare_related_values(parent, child, field)

        mlist = [(ldap.MOD_DELETE, field.ldap_field, values)]
        log.debug("LDAP.delete_relation %s :: %s"%(self.dn, ldap_log(mlist)))
        self.op_modify_ext(dn, mlist)

    def replace_relation(self, parent, child, field):
        dn = field.get_dn(parent, child)
        values = self.prepare_related_values(parent, child, field)

        mlist = [(ldap.MOD_REPLACE, field.ldap_field, values)]
        log.debug("LDAP.replace_relation %s :: %s"%(dn, ldap_log(mlist)))
        self.op_modify_ext(dn, mlist)

    def prepare_related_values(self, parent, child, field):
        """ relations are a represented as MultiValueFields
        instance values are returned as get_dn(), but this is true only for User
        - need to use ManyFields.get_dn()
        """
        if isinstance(child, models.Model):
            values = [field.as_value(parent, child)]
        elif isinstance(child, basestring):
            values = [child.encode('utf-8')]
        elif isinstance(child, list):
            pass
        else:
            raise Exception("Values must be a model instance, string or list")
        return values

    #
    #
    # OLD vs NEW
    #
    #

    def get_ldap_fields(self):
        ldap_fields = copy.deepcopy(self.parent_instance.ldap_fields)
        ldap_only_fields = copy.deepcopy(self.parent_instance.ldap_only_fields)
        ldap_fields.update(ldap_only_fields)
        return ldap_fields

    def model_fields_to_ldap_fields(self, values={}, extra={}, mode=''):
        a = {}
        changes = values
        for field, ldap_field in self.get_ldap_fields().iteritems():
            attr = getattr(self.parent_instance, field, '')
            if callable(attr):
                if mode == 'create':
                    # cn required on create
                    if changes:
                        a.update(self.as_ldap_value(field, attr()))
                else:
                    if changes.has_key(field):
                        a.update(self.as_ldap_value(field, attr()))

            else:
                if changes.has_key(field):
                    a.update(self.as_ldap_value(field, changes[field]['new']))
        a.update(extra)
        return a

    def as_ldap_value(self, field, value):
        ldap_fields = self.get_ldap_fields()
        if isinstance(ldap_fields[field], list):
            fields = ldap_fields[field]
        else:
            fields = [ldap_fields[field]]
        ldap_values = {}
        for f in fields:
            ldap_values[f] = to_ldap_value(value)
        return ldap_values

class DummyLdap(LDAPBridge):
    def delete(self, *a, **kw):
        log.debug("DummyLDAP.delete %s :: %s"%(self.dn, datetime.now()))
    def save(self, *a, **kw):
        log.debug("DummyLDAP.save %s :: %s"%(self.dn, datetime.now()))
    def create(self, *a, **kw):
        log.debug("DummyLDAP.create %s :: %s "%(self.dn, datetime.now()))
    def save_relation(self, *a, **kw):
        log.debug("DummyLDAP.save_relation %s :: %s "%(self.dn, datetime.now()))
    def replace_relation(self, *a, **kw):
        log.debug("DummyLDAP.replace_relation %s :: %s "%(self.dn, datetime.now()))
    def delete_relation(self, *a, **kw):
        log.debug("DummyLDAP.delete_relation %s :: %s "%(self.dn, datetime.now()))
    def create_raw(self, dn, mlist):
        log.debug("DummyLDAP.create_raw %s"%dn)
    def save_raw(self, dn, mlist):
        log.debug("DummyLDAP.save_raw %s"%dn)

class ReconnectingLDAPBridge(LDAPBridge):
    def __init__(self, parent, dn=None, **kwargs):
        super(ReconnectingLDAPBridge, self).__init__(parent, dn, **kwargs)
        self.ldap_class = ldap.ldapobject.ReconnectLDAPObject
        self.ldap_options = dict(
          uri=self.settings.uri,
          trace_level=settings.LDAP_TRACE_LEVEL,
          retry_max=settings.LDAP_RETRY_MAX,
          retry_delay=settings.LDAP_RETRY_DELAY,
        )
    def get_ldap_class(self):
        return self.ldap_class(**self.ldap_options)

    def _bind_as(self, bind_dn, bind_password, sticky=False, retry_number=0):
        try:
            self._get_connection().simple_bind_s(bind_dn.encode('utf-8'), bind_password.encode('utf-8'))
        except ldap.SERVER_DOWN, e:
            if retry_number == 0:
                self._connection = None
                return self._bind_as(bind_dn=bind_dn, bind_password=bind_password, sticky=sticky, retry_number=1)
        self._connection_bound = sticky

    def _get_bound_connection(self):
        if not self._connection: # _connection_bound irrelevant
            self._bind()
        return self._get_connection()

    def _get_connection(self):
        if self._connection is None:
            log.debug("Opening LDAP connection (%s)"%(self.settings.uri))
            self._connection = self.get_ldap_class()

            for opt, value in self.settings.CONNECTION_OPTIONS.iteritems():
                self._connection.set_option(opt, value)

            if self.settings.START_TLS:
                self._connection.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, 0)
                self._connection.start_tls_s()

        return self._connection

class PoolLDAPBridge(LDAPBridge):
    def op_add(self, dn, mlist):
        with self.connection as c:
            c.add_s(dn, mlist)

    def op_modify(self, dn, mlist):
        with self.connection as c:
            c.modify_s(dn, mlist)

    def op_modify_ext(self, dn, mlist):
        with self.connection as c:
            c.modify_ext_s(dn, mlist)

    def op_delete(self, dn):
        with self.connection as c:
            return c.delete_s(dn)

    def op_search(self, dn, scope, filters, attrs):
        with self.connection as c:
            return c.search_s(dn, scope, filters, attrs)

    def _get_bound_connection(self):
        return cm.connection(self.settings.BIND_DN, self.settings.BIND_PASSWORD)
    connection = property(_get_bound_connection)

def to_ldap_value(attr):
    if attr is None:
        return ''
    elif isinstance(attr, datetime):
        return format(attr, 'U').encode('utf8')
    elif isinstance(attr, unicode):
        return attr.encode('utf8')
    elif isinstance(attr, int):
        return str(attr)
    else:
        return attr

def my_import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

cls_lookup_table = {}
def ldap_cls(*args, **kwargs):
    ldap_cls = kwargs.pop('LDAP_CLASS', None) or settings.LDAP_CLASS
    if ldap_cls in cls_lookup_table:
        cls = cls_lookup_table[ldap_cls]
    else:
        ldap_cls_modules = ldap_cls.split('.')
        m = '.'.join(ldap_cls_modules[:-1])
        module = my_import(m)
        cls = getattr(module, ldap_cls_modules[-1])
        cls_lookup_table[ldap_cls] = cls
    return cls(*args, **kwargs)

