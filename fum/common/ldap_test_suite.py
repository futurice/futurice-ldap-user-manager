# encoding=utf8
"""
Base testcase for tests that interact with ldap
"""
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.test.client import Client

from mock import patch, MagicMock
from mockldap import MockLdap

from fum.ldap_helpers import test_user_ldap, ldap, ldap_cls
from fum.common.util import random_ldap_password, create_mandatory_groups
from django.db import models

import ldap

class LdapFunctionality(object):
    """
    Mocked LDAP class
     - add any testdata to LdapSuite.data (need better TestCase-specific loader?)
     - can be temporarily disabled by commenting out relevant lines in setUp, tearDown
    """
    data = [
    (settings.USER_DN, {'ou': ["People"]}),
    ("cn=Manager,ou=example,o=test", {"userPassword": ["ldaptest"]}),
    ("cn=alice,ou=example,o=test", {"userPassword": ["alicepw"]}),
    ("cn=bob,ou=other,o=test", {"userPassword": ["bobpw"]}),
    ("uid=fum3adm,ou=Administrators,ou=TopologyManagement,o=Netscaperoot", {"userPassword": ["njJc4RUWJVre"]}),
    ]
    directory = dict(data)

    def ldap_val(self, key, instance=None, dn=None, star=False, extra_attrs=[]):
        if hasattr(self.ldap.connection, 'directory'):
            if instance.__class__.__name__ == 'ManyRelatedManager':
                relations = {k.name:k for k in instance.instance.get_ldap_m2m_relations()}
                field = relations[instance.prefetch_cache_name]
                dn = field.get_dn(instance.instance, child=None)
            dn = dn or instance.get_dn()
            if star:
                r = self.ldap.connection.directory[dn]
            else:
                r = self.ldap.connection.directory[dn][key]
            return r
        else:
            try:
                extra_attrs = [key]
                if instance.__class__.__name__ == 'ManyRelatedManager':
                    relations = {k.name:k for k in instance.instance.get_ldap_m2m_relations()}
                    field = relations[instance.prefetch_cache_name]
                    model_funk = getattr(field, 'lval')(parent=instance.instance, extra_attrs=extra_attrs)
                    if star:
                        return model_funk
                    else:
                        return model_funk[key]
                elif isinstance(instance, models.Model):
                    if star:
                        return getattr(instance, 'lval')(extra_attrs=extra_attrs)
                    else:
                        return getattr(instance, 'lval')(extra_attrs=extra_attrs)[key]
                else: raise Exception("Does not compute")
            except ldap.NO_SUCH_OBJECT, e:
                raise KeyError(ldap.NO_SUCH_OBJECT)
                

    def save_safe(self, cls, kw, lookup, save_kw={}):
        """ Live testing against LDAP is tricky. If object exists, save to local database only """
        try:
            instance = cls(**kw)
            if hasattr(self, 'created_objects'):
                self.created_objects.append(instance)

            if save_kw:
                instance.save(**save_kw)
            else:
                instance.save()
        except ldap.ALREADY_EXISTS, e:
            if not getattr(settings, 'LDAP_MOCK', True):
                instance = cls(LDAP_CLASS='fum.ldap_helpers.DummyLdap', **kw)
                try:
                    instance.save()
                    instance.ldap = ldap_cls(parent=instance)
                except ValidationError, e:
                    instance = cls.objects.get(**lookup)
            else:
                raise
        return instance

    def setUp(self):
        if getattr(settings, 'LDAP_MOCK', True):
            self.mockldap = MockLdap(self.directory)
            self.mockldap.start()
        self.ldap = ldap_cls(parent=None)

        self.created_objects = []
        self.PASSWORD = random_ldap_password()
        self.USERNAME = 'testuser'
        self.django_user, self.user = self.create_user(self.USERNAME, email='test@fum.futurice.com', password=self.PASSWORD)
        self.client = Client()
        self.client.login(username=self.USERNAME, password=self.PASSWORD)

        self.assertTrue(test_user_ldap(self.USERNAME, self.PASSWORD))

    def tearDown(self):
        self.client.logout()
        self.user.delete()
        self.django_user.delete()

        # clean LDAP for test objects
        l = ldap_cls(parent=None)
        for k in self.created_objects:
            try:
                l.delete(dn=k.get_dn())
            except Exception, e:
                pass

        if getattr(settings, 'LDAP_MOCK', True):
            self.mockldap.stop()

    def create_user(self, username, email=None, password=None):
        from fum.models import Users
        password = password or random_ldap_password()
        email = email or '%s@fum.futurice.com'%username
        user = User.objects.create_user(username, email=email, password=password)
        fuser = self.save_safe(Users,
                kw=dict(first_name="Teemu", last_name="Testari", username=username, google_status=Users.ACTIVEPERSON),
                lookup=dict(username=username))
        fuser.set_ldap_password(password)
        return user, fuser
    
    def sudomode(self, client=None, user=None, password=None):
        from fum.models import Groups
        client = client or self.c
        user = user or self.apiuser
        password = password or self.API_PASSWORD
        g = self.save_safe(Groups,
                kw=dict(name=settings.IT_TEAM),
                lookup=dict(name=settings.IT_TEAM))
        g.users.add(user)
        response = client.post('/sudo/',
                {'password': password},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                REMOTE_USER=user.username)
        return response

class LdapSuite(LdapFunctionality, TestCase):
    pass

class LdapTransactionSuite(LdapFunctionality, TransactionTestCase):
    pass
