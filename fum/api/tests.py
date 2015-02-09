# encoding=utf8
"""
Tests for the API
"""
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test.utils import override_settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import pre_delete, post_delete, post_init, post_save, m2m_changed

from mock import patch, MagicMock, PropertyMock
from mockldap import MockLdap
import unittest
import ldap
from ldap import modlist

from fum.ldap_helpers import test_user_ldap, ldap_cls, PoolLDAPBridge
from fum.models import (
    Users, Servers, Groups, Projects, EMails, EMailAliases, BaseGroup,
    Resource, SSHKey,
)

import datetime, json, sys, copy, os, time
from pprint import pprint as pp
import sshpubkeys

from fum.api.changes import changes_save, rest_reverse
from fum.common.ldap_test_suite import LdapSuite, LdapTransactionSuite, random_ldap_password

from rest_framework.authtoken.models import Token
from rest_framework import status

create=[('objectClass', ['top', 'posixGroup', 'groupOfUniqueNames', 'mailRecipient', 'google', 'sambaGroupMapping', 'labeledURIObject']), ('sambaGroupType', '2'), ('gidNumber', '4001'), ('sambaSID', '{0}-9003'.format(settings.SAMBASID_BASE)), ('cn', 'TestGroup')]
update=[(2, 'sambaGroupType', '2'), (2, 'gidNumber', '4001'), (2, 'cn', 'TestGroup'), (2, 'objectClass', ['top', 'posixGroup', 'groupOfUniqueNames', 'mailRecipient', 'google', 'sambaGroupMapping', 'labeledURIObject']), (2, 'sambaSID', '{0}-9003'.format(settings.SAMBASID_BASE))]
update_nonexisting=[(2, 'nothere', '2'),]
add_empty=[(0, 'description', 'Blaa'),]
update_empty=[(2, 'description', 'Blaa'),]

add_user=[(0, 'uniqueMember', 'uid=hhol,{0}'.format(settings.USER_DN)),]
add_user_two=[(0, 'uniqueMember', 'uid=mmal,{0}'.format(settings.USER_DN)),]
add_user_three=[(0, 'uniqueMember', 'uid=mvih,{0}'.format(settings.USER_DN)),]

replace_user=[(2, 'uniqueMember', 'uid=hhol,{0}'.format(settings.USER_DN)),]
replace_user_two=[(2, 'uniqueMember', 'uid=mmal,{0}'.format(settings.USER_DN)),]

delete_user=[(1, 'uniqueMember', 'uid=hhol,{0}'.format(settings.USER_DN)),]

class RawLdapTestCase(TestCase):

    def test_mod(self):
        l = ldap_cls(parent=None, LDAP_CLASS='fum.ldap_helpers.LDAPBridge')
        dn = 'cn=TestGroup,{0}'.format(settings.PROJECT_DN)
        try:
            l.connection.delete_s(dn)
        except ldap.NO_SUCH_OBJECT, e:
            print e
        try:
            l.connection.add_s(dn, create)
        except ldap.ALREADY_EXISTS, e:
            print e
        l.connection.modify_s(dn, update)
        if 'test_live' in os.environ.get('DJANGO_SETTINGS_MODULE'):
            with self.assertRaises(ldap.OBJECT_CLASS_VIOLATION):
                l.connection.modify_s(dn, update_nonexisting)
        l.connection.modify_s(dn, update_empty)

        with self.assertRaises(ldap.TYPE_OR_VALUE_EXISTS):
            l.connection.modify_s(dn, add_empty)

        l.connection.modify_s(dn, add_user)
        l.connection.modify_s(dn, add_user_two)
        l.connection.modify_s(dn, add_user_three)

        l.connection.modify_s(dn, delete_user)

        l.connection.modify_s(dn, [(ldap.MOD_ADD, 'mail', 'me@mail.com'),])
        l.connection.modify_s(dn, [(ldap.MOD_ADD, 'mail', 'you@mail.com'),])
        l.connection.modify_s(dn, [(ldap.MOD_DELETE, 'mail', 'me@mail.com'),])
        #l.connection.modify_s(dn, [(ldap.MOD_DELETE, 'mail', None),])
        l.connection.delete_s(dn)


class ChangesTestCase(LdapSuite):

    def tearDown(self):
        Resource.objects.all().delete()
        super(ChangesTestCase, self).tearDown()

    def test_user_create(self):
        with patch('fum.api.changes.send_data') as o:
            user = Users.objects.create(first_name="A", last_name="B", username="xxx", google_status=Users.ACTIVEPERSON)
            sent_data = list(o.call_args)[0][0][0]
            self.assertTrue(all(k in sent_data.keys() for k in ['objectUrl', 'operation', 'timestamp', 'objectId', 'objectType', 'attrs']))
            self.assertEqual(sent_data['operation'], 'create')
            self.assertEqual(sent_data['objectId'], user.name)
            self.assertEqual(sent_data['objectType'], 'user')
            self.assertEqual(sent_data['objectUrl'], rest_reverse('users-detail', args=[user]))
            user.delete()

    def test_user_update(self):
        user = Users.objects.create(first_name="A", last_name="B", username="xxx", google_status=Users.ACTIVEPERSON)
        with patch('fum.api.changes.send_data') as o:
            user.last_name = 'Dekkari'
            user.save()
            sent_data = list(o.call_args)[0][0][0]
            self.assertEqual(sent_data['operation'], 'update')
        user.delete()

    def test_resource_create(self):
        name = 'woot'
        r = Resource(name=name, url='http://woot.com')
        r.content_object = self.user
        r.save()

        r.name = 'woof woof'
        r.save()

    def test_resource_create_without_schema(self):
        name = 'woot.com'
        r = Resource(name=name, url=name, content_object=self.user)
        r.save()
        self.assertEqual(r.url, 'http://%s'%name)

        name = 'spotify://woot.com'
        r = Resource(name=name, url=name, content_object=self.user)
        with self.assertRaises(ValidationError):
            r.save()

    def test_auditlog_internal(self):
        name = 'woot'
        with patch('fum.api.changes.send_data') as o:
            r = Resource(name=name, url='http://woot.com')
            r.content_object = self.user
            r.save()
            sent_data = list(o.call_args)[0][0][0]

class PermissionTestCase(LdapSuite):

    def setUp(self):
        super(PermissionTestCase, self).setUp()
        self.ttes = self.save_safe(Users,
                kw=dict(first_name="Teemu", last_name="Testari", username="ttes", google_status=Users.ACTIVEPERSON),
                lookup=dict(username='ttes'))

    def tearDown(self):
        self.ttes.delete()
        super(PermissionTestCase, self).tearDown()

    def test_search(self):
        results = self.user.ldap.fetch(settings.USER_DN, filters='(ou=*)', scope=ldap.SCOPE_BASE)
        self.assertEqual(results['ou'], ['People'])

    def test_delete_bad_dn(self):
        ERROR_CODE = 105
        try:
            self.assertEqual(ERROR_CODE, self.ldap.delete(dn="uid=ylamummo,{0}".format(settings.USER_DN))[0]) # mock
        except ldap.NO_SUCH_OBJECT, e:
            self.assertTrue(1) # live

    def test_only_owner_can_edit(self):
        user = self.ttes
        new_name = 'Heikki'
        response = self.client.post("/api/users/%s/"%user.username, {
            "first_name": new_name,
            },
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEquals(response.status_code, 400)
        self.assertEqual(Users.objects.get(username='ttes').first_name, user.first_name)

        response = self.client.post("/api/users/%s/"%user.username, {
            "phone1": '001235124',
            },
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEqual(json.loads(response.content)['__all__'][0], 'Permission denied')
        self.assertEquals(response.status_code, 400)

    def test_sudoer_can_edit(self):
        user = self.ttes
        new_name = 'Heikki'

        # test sudo failure
        response = self.client.post('/sudo/',
                {'password':self.PASSWORD},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                REMOTE_USER=self.USERNAME)
        self.assertEquals(response.status_code, 401)

        # add to TeamIT
        g = self.save_safe(Groups,
                kw=dict(name=settings.IT_TEAM),
                lookup=dict(name=settings.IT_TEAM))
        try:
            g.users.add(self.user)
        except ldap.TYPE_OR_VALUE_EXISTS, e: # live LDAP not cleaned
            pass
        response = self.client.post('/sudo/',
                {'password': self.PASSWORD},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                REMOTE_USER=self.USERNAME)
        self.assertEquals(response.status_code, 200)

        response = self.client.post("/api/users/%s/"%user.username, {
            "phone1": '001235124',
            },
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',
            REMOTE_USER=self.USERNAME)
        self.assertEquals(response.status_code, 200)

    def test_user_can_edit_non_restricted_fields(self):
        # can not edit other users without SUDO/ownership
        user = self.ttes
        new_name = 'Heikki'
        response = self.client.post("/api/users/%s/"%user.username, {
            "first_name": new_name,
            },
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEquals(response.status_code, 400)
        self.assertEqual(Users.objects.get(username='ttes').first_name, user.first_name)

        response = self.client.post("/api/users/%s/"%user.username, {
            "phone1": '001235124',
            },
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEqual(json.loads(response.content)['__all__'][0], 'Permission denied')
        self.assertEquals(response.status_code, 400)

    def test_user_can_not_m2m_protected_groups(self):
        user = self.ttes
        name = 'Futurice'
        response = self.client.post("/api/groups/", {
            "name": name,
            })
        self.assertEquals(response.status_code, 400)

        futurice = self.save_safe(Groups,
                kw=dict(name=name),
                lookup=dict(name=name))

        response = self.client.delete("/api/groups/{0}/".format(name))
        self.assertEquals(response.status_code, 403)

        response = self.client.get("/api/groups/{0}/".format(name))
        self.assertEquals(response.status_code, 200)

        with self.assertRaises(ValidationError):
            response = self.client.post("/api/groups/{0}/users/".format(name),
                    {"items": [user.username]})
            self.assertEquals(response.status_code, 403)

class TokenPermissionTestCase(LdapSuite):

    def setUp(self):
        super(TokenPermissionTestCase, self).setUp()
        self.client = Client()
        user,_ = User.objects.get_or_create(username='Bob')
        self.token = Token.objects.create(user=user)
        self.token_signature = 'Token '+self.token.key

        self.ttes = self.save_safe(Users,
                kw=dict(first_name="Teemu", last_name="Testari", username="ttes", google_status=Users.ACTIVEPERSON),
                lookup=dict(username='ttes'))

    def test_token_auth(self):
        response = self.client.get("/api/")
        self.assertEqual(response.status_code, 403)

        response = self.client.get("/api/",
                {},
                HTTP_AUTHORIZATION=self.token_signature)
        self.assertEqual(response.status_code, 200)
        user = Users.objects.get(username=self.USERNAME)

        self.assertEqual(Users.objects.get(username=self.USERNAME).active_in_planmill, Users.PLANMILL_DISABLED)
        response = self.client.post("/api/users/%s/"%user.username, {
            "active_in_planmill": Users.PLANMILL_ACTIVE,
            },
            HTTP_AUTHORIZATION=self.token_signature,
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Users.objects.get(username=self.USERNAME).active_in_planmill, Users.PLANMILL_ACTIVE)

        response = self.client.post("/api/users/%s/"%user.username, {
            "active_in_planmill": str(Users.PLANMILL_INACTIVE),
            },
            HTTP_AUTHORIZATION=self.token_signature,
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Users.objects.get(username=self.USERNAME).active_in_planmill, Users.PLANMILL_INACTIVE)

        response = self.client.post("/api/users/%s/"%user.username, {
            "active_in_planmill": Users.PLANMILL_ACTIVE,
            },
            HTTP_AUTHORIZATION=self.token_signature,
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Users.objects.get(username=self.USERNAME).active_in_planmill, Users.PLANMILL_ACTIVE)

        # restricted records can be modified via API, with a valid token
        response = self.client.post("/api/users/%s/"%self.ttes.username, {
            "username": 'abc',
            },
            HTTP_AUTHORIZATION=self.token_signature,
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEqual(response.status_code, 200)

        response = self.client.post("/api/users/%s/"%self.ttes.username, {
            "active_in_planmill": 1,
            },
            HTTP_AUTHORIZATION=self.token_signature,
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEqual(response.status_code, 200)

    def test_token_access_planmill(self):
        response = self.client.get("/api/users/{0}/".format(self.ttes.username),
                {},
                HTTP_AUTHORIZATION=self.token_signature)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(['active_in_planmill' in k for k in json.loads(response.content)])

        response = self.client.get("/api/users/", {
            'fields': 'id,active_in_planmill',
            'limit': 0,
            },
            HTTP_AUTHORIZATION=self.token_signature)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(['active_in_planmill' in k for k in json.loads(response.content)]))


class LdapSanityCase(TestCase):
    # Test that mocks for LDAP are working throughout Django

    data = [
    ("uid=fum3adm,ou=Administrators,ou=TopologyManagement,o=Netscaperoot", {"userPassword": ["njJc4RUWJVre"]}),
    ("uid=ttes,{0}".format(settings.USER_DN), {"userPassword": ["secret"], "uidNumber": ["2001"],}),
    ("uid=testuser,{0}".format(settings.USER_DN), {"userPassword": ["secret"], "uidNumber": ["2003"],}),
    ]
    directory = dict(data)

    def setUp(self):
        self.mockldap = MockLdap(self.directory)
        self.mockldap.start()
        self.ldap = ldap_cls(parent=None, uri='ldap://localhost', LDAP_CLASS='fum.ldap_helpers.LDAPBridge')

    def tearDown(self):
        self.mockldap.stop()

    def test_signals_mocked(self):
        # ReconnectingLDAPBridge re-uses initial connection
        option_count = len(settings.LDAP_CONNECTION_OPTIONS)
        tls = ['initialize'] + ['set_option']*option_count + ['initialize']
        self.assertEquals(self.ldap.connection.methods_called(),
                tls +['start_tls_s', 'simple_bind_s'])
        server = Servers.objects.create(name="Testiserveri222", description="Testiserverin kuvaus")
        methods_called = self.ldap.connection.methods_called()
        self.assertEquals(methods_called,
                tls +['start_tls_s', 'simple_bind_s'])
        #tls+['start_tls_s', 'simple_bind_s',] + tls + ['start_tls_s', 'simple_bind_s', 'add_s', 'add_s'])

        server.delete()
        methods_called = self.ldap.connection.methods_called()
        self.assertEquals(methods_called,
                tls +['start_tls_s', 'simple_bind_s'])
        #tls+['start_tls_s', 'simple_bind_s',] + tls + ['start_tls_s', 'simple_bind_s', 'add_s', 'add_s', 'delete_s', 'delete_s'])
    def test_down(self):
        return
        if 'test_live' in os.environ.get('DJANGO_SETTINGS_MODULE'):
            lcon = ldap_cls(parent=None, uri='ldap://localhost', LDAP_CLASS='fum.ldap_helpers.ReconnectingLDAPBridge')
            with self.assertRaises(ldap.SERVER_DOWN):
                lcon.connection


class LdapTestCase(LdapSuite):

    def setUp(self):
        super(LdapTestCase, self).setUp()
        pname = 'PTestiProjekti'
        sname = 'TestiServer'
        self.user2 = self.save_safe(Users,
                kw=dict(first_name="TIina", last_name="Testaaja", username='tite', google_status=Users.ACTIVEPERSON),
                lookup=dict(username='tite'))
        self.project = self.save_safe(Projects,
                kw=dict(name=pname, description="Testiprojektin kuvaus"),
                lookup=dict(name=pname))
        self.server = self.save_safe(Servers,
                kw=dict(name=sname, description="Testiserverin kuvaus"),
                lookup=dict(name=sname))

    def tearDown(self):
        self.user2.delete()
        self.project.delete()
        self.server.delete()
        super(LdapTestCase, self).tearDown()

    def test_delete_relation(self):
        server_name = 'test_server_1'
        server = self.save_safe(Servers, kw=dict(name=server_name), lookup=dict(name=server_name))
        mail = '%s@futurice.com'%server_name
        email = EMails(address=mail, content_object=server)
        server.email.add(email)
        self.assertEqual(self.ldap_val('mail', server), [mail])
        server.email.remove(email)
        with self.assertRaises(KeyError):
            self.ldap_val('mail', server)
        

    def test_save_sudoer(self):
        data = ('cn=it-team,{0}'.format(settings.SUDO_DN),
                {'sudoHost': ['ALL'],
                'sudoUser': ['ileh', 'ojar',],
                'cn': ['it-team']})
        server_name = 'it-team'
        server = self.save_safe(Servers, kw=dict(name=server_name), lookup=dict(name=server_name))
        for username in data[1]['sudoUser']:
            django_test_user, user = self.create_user(username)
            try:
                server.sudoers.add(user)
            except ldap.TYPE_OR_VALUE_EXISTS, e:
                pass

    def test_create_server(self):
        self.serverminion = self.save_safe(Servers, dict(name="Testiserveri222", description="Testiserverin kuvaus"), lookup=dict(name="Testiserveri222"))
        self.serverminion.delete()

    def test_create_without_saving_to_ldap(self):
        username = 'aankdbonly'
        user = Users(first_name="Aku", last_name="Ankka", username=username, google_status=Users.ACTIVEPERSON, LDAP_CLASS='fum.ldap_helpers.DummyLdap')
        user.save()
        user.ldap = ldap_cls(parent=user, LDAP_CLASS='fum.ldap_helpers.LDAPBridge')
        with self.assertRaises(KeyError):
            self.ldap_val('givenName', user)

        self.assertTrue(Users.objects.get(username=username))

    def test_create_without_saving_to_ldap_with_pk(self):
        username = 'aank'
        user = Users(id=3001, first_name="Aku", last_name="Ankka", username=username, google_status=Users.ACTIVEPERSON, LDAP_CLASS='fum.ldap_helpers.DummyLdap')
        user.save()
        self.assertTrue(Users.objects.get(username=username))

    def test_create_email_without_saving_to_ldap(self):
        username = 'aank3'

        user = self.save_safe(Users,
                kw=dict(id=3001, first_name="Aku", last_name="Ankka", username=username, google_status=Users.ACTIVEPERSON),
                lookup=dict(username=username),
                save_kw=dict(force_insert=True))

        with self.assertRaises(KeyError):
            self.ldap_val('mail', user)

        email = 'paddy@mock.com'
        with self.settings(LDAP_CLASS='fum.ldap_helpers.DummyLdap'):
            em = EMails(address=email, content_object=user)
            em.save()

        with self.assertRaises(KeyError):
            self.ldap_val('mail', user)

        user.delete()

    def test_create_user_with_email(self):
        username = 'aank2'
        try:
            Users(username=username).ldap.delete()
        except ldap.NO_SUCH_OBJECT, e:
            print e
        user = self.save_safe(Users,
                kw=dict(first_name="Aku", last_name="Ankka", username=username, google_status=Users.ACTIVEPERSON),
                lookup=dict(username=username))

        with self.assertRaises(KeyError):
            self.ldap_val('mail', user)
        self.assertEqual(Users.objects.get(username=username).get_email(), None)

        email = 'paddy@mock.com'
        em = EMails(address=email, content_object=user)
        em.save()

        self.assertEqual(self.ldap_val('mail', user)[0], email)
        self.assertEqual(Users.objects.get(username=username).get_email().address, email)

        user.delete()

    def test_create_email(self):
        email = 'wizard@oz.com'

        em = EMails(address=email, content_object=self.user)
        em.save()

        self.assertEqual(self.ldap_val('mail', self.user)[0], email)
        self.assertEqual(Users.objects.get(username=self.user.username).get_email().address, email)

    def test_user_modify(self):
        username = 'beatlebug'
        user = self.save_safe(Users,
                kw=dict(first_name="Aku", last_name="Ankka", username=username, google_status=Users.ACTIVEPERSON),
                lookup=dict(username=username))
        #user = self.user
        # ^ really wierd Mixin behaviour, not resetting state on .save() when running full suite
        user.first_name = 'Heikki'
        user.save()
        self.assertEqual(self.ldap_val('givenName', user)[0], 'Heikki')

        user.first_name = 'Teemu'
        user.save()
        self.assertEqual(self.ldap_val('givenName', user)[0], 'Teemu')

    def test_project_m2m(self):
        self.project.users.add(self.user)
        self.assertEqual(self.project.users.all()[0], self.user)
        self.assertTrue(any("uid=%s"%self.user.username in user for user in self.ldap_val('uniqueMember', self.project)))

    def test_server_sudoers(self):
        self.server.users.add(self.user)
        self.server.sudoers.add(self.user2)
        sudoers = self.ldap_val('sudoUser', self.server.sudoers)
        sudoers_in_beginning = len(sudoers)
        self.assertTrue(len(sudoers) > 0)
        self.server.sudoers.add(self.user)
        sudoers = self.ldap_val('sudoUser', self.server.sudoers)
        self.assertEqual(len(sudoers), sudoers_in_beginning + 1)
        members = self.ldap_val('uniqueMember', instance=self.server)
        self.assertTrue(self.user.get_dn() in members)

        sudoers = self.ldap_val('sudoUser', self.server.sudoers)
        self.assertTrue(self.user.username in sudoers)

    def test_server_m2m_user(self):
        self.server.users.add(self.user)
        members = self.ldap_val('uniqueMember', instance=self.server)
        self.assertEqual([self.user.get_dn()], members)

        # TODO: dn=self.server should be enough to determine DN for 'sudoUser'
        dn = self.server.get_ldap_sudoers_dn()
        with self.assertRaises(KeyError):
            sudoers = self.ldap_val('sudoUser', self.server.sudoers)

    def test_server_m2m_sudoer(self):
        self.server.sudoers.add(self.user)
        sudoers = self.ldap_val('sudoUser', self.server.sudoers)
        self.assertEqual(sudoers, [self.user.get_ldap_id_value()])

    def test_server_m2m_functions(self):
        self.assertEqual(['uniqueMember', 'sudoUser'], [k.ldap_field for k in self.server.get_ldap_m2m_relations()])
        self.assertEqual(['users', 'sudoers'], [k.name for k in self.server.get_ldap_m2m_relations()])
        self.assertEqual([('users', 'uniqueMember'), ('sudoers', 'sudoUser')], [(k.name, k.ldap_field) for k in self.server.get_ldap_m2m_relations()])

    def test_set_value(self):
        from ldap import modlist
        modified_values = {'key': 'new'}
        self.assertEquals(modlist.modifyModlist({}, modified_values), [(0, 'key', 'new')])

        mlist = self.ldap.get_modify_modlist(modified_values)
        self.assertEquals(mlist, [(2, 'key', 'new')])

    def test_set_to_empty(self):
        from ldap import modlist
        modified_values = {'key': ''}
        self.assertEquals(modlist.modifyModlist({}, modified_values), [])
        self.assertEquals(modlist.modifyModlist({'key': 'old-value'}, {'key': ''}), [(1, 'key', None)])

        mlist = self.ldap.get_modify_modlist(modified_values)
        self.assertEquals(mlist, [(2, 'key', None)])

        modified_values = {'key': 'foo'}
        self.assertEquals(modlist.modifyModlist({'key': ''}, {'key': 'foo'}), [(0, 'key', 'foo')])
        mlist = self.ldap.get_modify_modlist(modified_values)
        self.assertEquals(mlist, [(2, 'key', 'foo')])

        self.user.title = 'Title'
        self.user.save()
        self.assertEquals(self.user.lval().get('title'), ['Title'])

        self.user.title = ''
        self.user.save()
        self.assertEquals(self.user.lval().get('title'), None)

        self.user.title = 'NewTitle'
        self.user.save()
        self.assertEquals(self.user.lval().get('title'), ['NewTitle'])

class ApiTestCase(LdapTransactionSuite):

    def setUp(self):
        super(ApiTestCase, self).setUp()

        # Create API user
        self.API_USERNAME = 'TestAPI'
        self.API_EMAIL = 'test@fum.futurice.com'
        self.API_PASSWORD = random_ldap_password()
        self.django_test_user, self.apiuser = self.create_user(self.API_USERNAME, email=self.API_EMAIL, password=self.API_PASSWORD)
        
        # Set permissions for user
        models = [Users, Servers, Groups, Projects]
        for model in models:
            content_type = ContentType.objects.get_for_model(model)
            permission_add = Permission.objects.get(content_type=content_type, codename='add_%s'%model.__name__.lower())
            permission_del = Permission.objects.get(content_type=content_type, codename='delete_%s'%model.__name__.lower())
            permission_edi = Permission.objects.get(content_type=content_type, codename='change_%s'%model.__name__.lower())
            self.django_test_user.user_permissions.add(permission_add, permission_del, permission_edi)

        self.c = Client()
        self.c.login(username=self.API_USERNAME, password=self.API_PASSWORD)

    def tearDown(self):
        #Delete objects that may have been saved to db/ldap and not deleted
        try:    
            g = Groups.objects.get(name="TestGroup")
            g.delete()
        except (ObjectDoesNotExist, ldap.NO_SUCH_OBJECT):
            pass

        try:
            s = Servers.objects.get(name="TestServer")
            s.delete()
        except (ObjectDoesNotExist, ldap.NO_SUCH_OBJECT):
            pass

        for k in ['PTestProject','PTestProjectX','PTestProjectX2']:
            try:
                p = Projects.objects.get(name=k)
                p.delete()
            except (ObjectDoesNotExist, ldap.NO_SUCH_OBJECT):
                pass

        self.apiuser.delete()
        super(ApiTestCase, self).tearDown()

    def test_status(self):
        url = rest_reverse('users-status', args=[self.apiuser.username])
        response = self.c.get(url)
        self.assertEquals(json.loads(response.content), {'status': 'active'})
        self.sudomode()
        response = self.c.post(url,
                {"status": Users.USER_DISABLED,},
                HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEquals(response.status_code, 200)
        response = self.c.get(url)
        self.assertEquals(json.loads(response.content), {'status': 'disabled'})

    def test_email_integrity(self):
        mail = 'pentti@futurice.com'
        self.user.email.add(EMails(address=mail, content_object=self.user))

        group_mail = u"test.Group1@futurice.com"
        project_name = 'PTestGroup'
        try:
            l = ldap_cls(parent=None)
            l.delete(dn=Projects(name=project_name).get_dn())
        except ldap.NO_SUCH_OBJECT, e:
            pass

        try:
            response = self.c.post("/api/projects/", {
                "name": project_name,
                "email": group_mail,
                })
            self.assertEquals(response.status_code, 201)
        except ldap.ALREADY_EXISTS:
            pass
        project = Projects.objects.get(name=project_name)
        self.assertEqual(project.get_email().address, group_mail)
        self.assertEqual(self.ldap_val('mail', project), [group_mail])

        response = self.client.post("/api/projects/%s/"%project.name,
                {"description": 'A project',},
                HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEqual(project.get_email().address, group_mail)
        self.assertEqual(self.ldap_val('mail', project), [group_mail])

        with self.assertRaises(ValidationError):
            response = self.client.post("/api/projects/%s/"%project.name,
                    {"email": mail,},
                    HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEqual(project.get_email().address, group_mail)
        self.assertEqual(self.ldap_val('mail', project), [group_mail])

        response = self.client.post("/api/projects/%s/"%project.name,
                {"email": '',},
                HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEqual(project.get_email(), None)
        with self.assertRaises(KeyError):
            self.ldap_val('mail', project)

    def test_get_user_by_email(self):
        response = self.c.post("/api/users/%s/"%self.apiuser.username,
                {"email": self.API_EMAIL,},
                HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        response = self.c.get("/api/users/", {"email": self.API_EMAIL,},)
        self.assertEqual(json.loads(response.content)['results'][0]['username'], self.apiuser.username)
        self.client.delete("/api/users/%s"%self.apiuser.username)

    def test_api_root(self):
        response = self.c.get("/api/", {})

        self.assertContains(response, "users")
        self.assertContains(response, "groups")
        self.assertContains(response, "servers")
        self.assertContains(response, "projects")

    def test_user(self):
        name = "testusermikko"
        mail = "test.user@futurice.com"
        response = self.c.post("/api/users/", {
            "username": name,
            "first_name": "Test",
            "last_name": "User",
            "google_status": Users.ACTIVEPERSON,
            "email": mail
            })
        self.assertEquals(response.status_code, 201)

        user = Users.objects.get(username=name)

        django_user,_ = User.objects.get_or_create(username=name, is_active=True)
        django_user.set_password(name)
        django_user.save()
        django_user_client = self.client
        self.djc = Client()
        self.djc.login(username=name, password=name)
        
        response = self.c.get("/api/users/", {})
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, mail)
        self.assertEqual(self.ldap_val('mail', user), [mail])

        response = self.c.get("/api/users/%s/"%name, {})
        self.assertContains(response, name)

        new_mail = "test.emailmikko@futurice.com"
        response = self.c.post('/api/users/%s/'%name,
                {'email': new_mail},
               HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEquals(response.status_code, 400)

        response = self.djc.post('/api/users/%s/'%name,
                {'email': new_mail},
               HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEquals(response.status_code, 200)

        response = self.c.get("/api/users/%s/"%name, {})

        self.assertContains(response, new_mail)
        self.assertEqual(self.ldap_val('mail', user), [new_mail])

        response = self.c.delete("/api/users/%s/"%name)
        self.assertEquals(response.status_code, 204)
        with self.assertRaises(KeyError):
            self.ldap_val('mail', user)

        response = self.c.get("/api/users/", {})
        self.assertNotContains(response, name)

    def test_group(self):
        try:
            response = self.c.post("/api/groups/", {
                "name": "TestGroup",
                "description": "Test group1234",
                "email":"test.Group1@futurice.com"
                })
            self.assertEquals(response.status_code, 201)
        except ldap.ALREADY_EXISTS:
            pass

        response = self.c.get("/api/groups/", {})
        self.assertContains(response, "group1234")

        response = self.c.get("/api/groups/TestGroup/", {})
        self.assertContains(response, "TestGroup")
        self.assertContains(response, "test.Group1@futurice.com")

        response = self.c.post("/api/groups/TestGroup/",
                {'email': "test.groupm@futurice.com"},
               HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEquals(response.status_code, 200)
        response = self.c.get("/api/groups/TestGroup/", {})
        self.assertContains(response, "test.groupm@futurice.com")

        g = self.save_safe(Groups,
                kw=dict(name=settings.IT_TEAM),
                lookup=dict(name=settings.IT_TEAM))

        response = self.c.post("/api/groups/TestGroup/", {
            "editor_group": g.name,
            },
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEquals(response.status_code, 400)

        g.users.add(self.apiuser)
        response = self.c.post('/sudo/',
                {'password': self.API_PASSWORD},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                REMOTE_USER=self.API_USERNAME)

        self.assertEquals(response.status_code, 200)
        response = self.c.post("/api/groups/TestGroup/", {
            "editor_group": g.name,
            },
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEquals(response.status_code, 200)

        response = self.c.delete("/api/groups/TestGroup/", {})
        self.assertEquals(response.status_code, 204)

        response = self.c.get("/api/groups/", {})
        self.assertNotContains(response, "group1234")

    def test_server(self):
        response = self.c.post("/api/servers/", {
            "name": "TestServer",
            "description": "Test server1234",
            "email":"testServer1@futurice.com"
            })
        self.assertEquals(response.status_code, 201)

        response = self.c.get("/api/servers/", {})
        self.assertContains(response, "server1234")
        self.assertContains(response, "testServer1@futurice.com")

        response = self.c.get("/api/servers/TestServer/", {})
        self.assertContains(response, "TestServer")

        response = self.c.post("/api/servers/TestServer/",
                {'email': "test.serverm@futurice.com"},
               HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEquals(response.status_code, 200)
        response = self.c.get("/api/servers/TestServer/", {})
        self.assertContains(response, "test.serverm@futurice.com")

        response = self.c.delete("/api/servers/TestServer/", {})
        self.assertEquals(response.status_code, 204)

        response = self.c.get("/api/servers/", {})
        self.assertNotContains(response, "server1234")

    def test_project_create(self):
        response = self.c.post("/api/projects/", {
            "name": "PTestProjectX",})
        self.assertEqual(response.status_code, 201)
        response = self.c.post("/api/projects/", {
            "name": "PTestProjectX2",
            "description": "",})
        self.assertEqual(response.status_code, 201)

    def test_project(self):
        pname = 'PTestProject'
        response = self.c.post("/api/projects/", {
            "name": pname,
            "description": "Test project1234",
            "email":"TestProject21@futurice.com"
            })
        self.assertEquals(response.status_code, 201)

        response = self.c.get("/api/projects/", {})
        self.assertContains(response, "project1234")
        self.assertContains(response, "TestProject21@futurice.com")

        response = self.c.get("/api/projects/%s/"%pname, {})
        self.assertContains(response, pname)

        response = self.c.post("/api/projects/%s/"%pname,
                {'email': "test.projectm@futurice.com"},
               HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        self.assertEquals(response.status_code, 200)
        response = self.c.get("/api/projects/%s/"%pname, {})
        self.assertContains(response, "test.projectm@futurice.com")

        response = self.c.delete("/api/projects/%s/"%pname, {})
        self.assertEquals(response.status_code, 204)

        response = self.c.get("/api/projects/", {})
        self.assertNotContains(response, "project1234")


    def test_set_homedir(self):
        response = self.c.post("/api/users/", {
            "username": "testhomediruser",
            "first_name": "Home",
            "last_name": "DirUser",
            "google_status": Users.ACTIVEPERSON,
            "home_directory": "/home/ci/testhomediruser",
            })
        self.assertEquals(response.status_code, 201)
        
        response = self.c.get("/api/users/", {})
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "testhomediruser")
        self.assertContains(response, "/home/ci/testhomediruser")


        u = Users.objects.get(username="testhomediruser")
        u.delete()

        response = self.c.get("/api/users/", {})
        self.assertEquals(response.status_code, 200)
        self.assertNotContains(response, "testhomediruser")

    def test_del(self):
        models = [[Servers,None], [Groups,None], [Projects,'PProjectName']]
        for model, name in models:
            model_name = model.__name__.lower()
            name = copy.deepcopy(name or model.__name__.lower())
            response = self.c.post("/api/%s/"%model_name, {
                "name": name
            })
            self.assertEquals(response.status_code, 201)

            content_type = ContentType.objects.get_for_model(model)
            permission_del = Permission.objects.get(content_type=content_type, codename='delete_%s'%model_name)
            self.django_test_user.user_permissions.remove(permission_del)

            url = "/api/%s/%s/"%(model_name, name)
            response = self.c.delete(url, {})
            self.assertEquals(response.status_code, 403)

            permission_del = Permission.objects.get(content_type=content_type, codename='delete_%s'%model_name)
            self.django_test_user.user_permissions.add(permission_del)

            response = self.c.delete("/api/%s/%s/"%(model_name, name),{})
            self.assertEquals(response.status_code, 204)

            try:
                model.objects.get(name=name).delete()
            except Exception as e:
                print e

            

class ApiLimitsTestCase(LdapSuite):

    def setUp(self):
        super(ApiLimitsTestCase, self).setUp()

        # Create API user
        self.API_USERNAME = 'TestAPI'
        self.API_EMAIL = 'test@fum.futurice.com'
        self.API_PASSWORD = random_ldap_password()
        self.django_test_user, self.apiuser = self.create_user(self.API_USERNAME, email=self.API_EMAIL, password=self.API_PASSWORD)

        self.c = Client()
        self.c.login(username=self.API_USERNAME, password=self.API_PASSWORD)

        self.group = self.save_safe(Groups, dict(name='ListTestGroup', description="Test"), lookup=dict(name='ListTestGroup'))
        self.server = self.save_safe(Servers, dict(name='ListTestServer', description="Test"), lookup=dict(name='ListTestServer'))
        self.project = self.save_safe(Projects, dict(name='PListTestProject', description="Test"), lookup=dict(name='PListTestProject'))

    def tearDown(self):
        self.apiuser.delete()
        self.group.delete()
        self.server.delete()
        self.project.delete()
        super(ApiLimitsTestCase, self).tearDown()

    def test_groups_default(self):
        response = self.c.get("/api/groups/", {})

        self.assertContains(response, "name")
        self.assertContains(response, "description")
        self.assertContains(response, "email")
        self.assertContains(response, "email_aliases")
        self.assertContains(response, "editor_group")
        self.assertContains(response, "users")

    def test_servers_default(self):
        response = self.c.get("/api/servers/", {})

        self.assertContains(response, "name")
        self.assertContains(response, "description")
        self.assertContains(response, "email")
        self.assertContains(response, "email_aliases")
        self.assertContains(response, "editor_group")
        self.assertContains(response, "users")
        self.assertContains(response, "sudoers")

    def test_projects_default(self):
        response = self.c.get("/api/projects/", {})
        self.assertContains(response, "name")
        self.assertContains(response, "description")
        self.assertContains(response, "email")
        self.assertContains(response, "email_aliases")
        self.assertContains(response, "editor_group")
        self.assertContains(response, "users")

    def test_users_default(self):
        response = self.c.get("/api/users/", {})

        self.assertContains(response, "count")
        self.assertContains(response, "next")
        self.assertContains(response, "previous")
        self.assertContains(response, "results")
        self.assertContains(response, "first_name")
        self.assertContains(response, "last_name")
        self.assertContains(response, "username")
        self.assertContains(response, "title")
        self.assertContains(response, "phone1")
        self.assertContains(response, "phone2")
        self.assertContains(response, "email")
        self.assertContains(response, "skype")
        self.assertContains(response, "google_status")
        self.assertContains(response, "email_aliases")

    def test_groups_limit(self):
        response = self.c.get("/api/groups/?limit=0", {})

        self.assertContains(response, "name")
        self.assertContains(response, "description")
        self.assertNotContains(response, "email")
        self.assertNotContains(response, "email_aliases")
        self.assertNotContains(response, "editor_group")
        self.assertNotContains(response, "users")

    def test_servers_limit(self):
        response = self.c.get("/api/servers/?limit=0", {})

        self.assertContains(response, "name")
        self.assertContains(response, "description")
        self.assertNotContains(response, "email")
        self.assertNotContains(response, "email_aliases")
        self.assertNotContains(response, "editor_group")
        self.assertNotContains(response, "users")
        self.assertNotContains(response, "sudoers")

    def test_projects_limit(self):
        response = self.c.get("/api/projects/?limit=0", {})

        self.assertContains(response, "name")
        self.assertContains(response, "description")
        self.assertNotContains(response, "email")
        self.assertNotContains(response, "email_aliases")
        self.assertNotContains(response, "editor_group")
        self.assertNotContains(response, "users")

    def test_users_limit(self):
        response = self.c.get("/api/users/?limit=0", {})

        self.assertNotContains(response, "count")
        self.assertNotContains(response, "next")
        self.assertNotContains(response, "previous")
        self.assertNotContains(response, "results")
        self.assertContains(response, "first_name")
        self.assertContains(response, "last_name")
        self.assertContains(response, "username")
        self.assertContains(response, "email")
        self.assertNotContains(response, "title")
        self.assertNotContains(response, "phone1")
        self.assertNotContains(response, "phone2")
        self.assertNotContains(response, "skype")
        self.assertNotContains(response, "google_status")
        self.assertNotContains(response, "email_aliases")

class ChaosException(Exception):
    pass

class DataIntegrityTestCase(LdapTransactionSuite):
    """
    Transanctional testing.

    save()
     -> signals:
       pre_save
       post_save
     -> save_ldap()

    changes.send_data is called in signals.post_save.changes
    """

    def setUp(self):
        super(DataIntegrityTestCase, self).setUp()
        self.signals = []
        self.cleanup = []

    def tearDown(self):
        super(DataIntegrityTestCase, self).tearDown() # keep at top
        for signal in self.signals:
            self.rem_signal(signal['type'], **signal['kw'])
        for model in self.cleanup:
            if isinstance(model, BaseGroup):
                for k in model.users.all():
                    k.delete()
            # deleting against ldap not implemented (19/8)
            #model.delete()

    def add_signal(self, signal, **kwargs):
        signal.connect(**kwargs)
        kwargs.pop('receiver', None)
        self.signals.append({'type': signal, 'kw': kwargs})

    def rem_signal(self, signal, **kwargs):
        signal.disconnect(**kwargs)

    def test_save_exception_in_changes(self):
        name = 'Abe0'
        with patch('fum.common.signals.injection') as o:
            o.side_effect = ChaosException
            server_mock = Servers(name=name)
            try:
                server = self.save_safe(Servers, dict(name=name, description="Abradabradaa"), lookup=dict(name=name))
            except ChaosException, e:
                pass
            with self.assertRaises(Servers.DoesNotExist):
                Servers.objects.get(name=name)

            with self.assertRaises(KeyError):
                self.ldap_val('cn', server_mock)

    def test_save_exception_in_signal_postsave(self):
        name = 'Abe1'
        with patch('fum.common.signals.injection') as o:
            self.add_signal(post_save, receiver=o, sender=Servers, dispatch_uid='test_mocked_handler')

            o.side_effect = ChaosException
            server_mock = Servers(name=name)
            with self.assertRaises(ChaosException):
                server = self.save_safe(Servers, dict(name=name, description="Abradabradaa"), lookup=dict(name=name))
            with self.assertRaises(Servers.DoesNotExist):
                Servers.objects.get(name=name)
            with self.assertRaises(KeyError):
                self.ldap_val('cn', server_mock)

        self.assertEqual(o.call_count, 1)

    def test_save(self):
        name = 'Abe2'
        server_mock = Servers(name=name)
        server = self.save_safe(Servers, dict(name=name, description="Abradabradaa"), lookup=dict(name=name))
        self.cleanup.append(server)
        # .save -> signal -> .save_ldap()
        self.assertEqual(Servers.objects.get(name=name).name, name)
        self.assertEqual(self.ldap_val('cn', server_mock), [name])

    def test_sudoers(self):
        name = 'AbSudoServer'
        server_mock = Servers(name=name)
        server = self.save_safe(Servers, dict(name=name, description="AbSudo"), lookup=dict(name=name))

        server.users.add(self.user)
        self.assertEqual(self.ldap_val('uniqueMember', server.users), [self.user.get_dn()])

        server.sudoers.add(self.user)
        self.assertEqual(self.ldap_val('sudoUser', server.sudoers), [self.user.username])

        server.sudoers.remove(self.user)
        try:
            self.ldap_val('sudoUser', server.sudoers)
            self.assertEqual(self.ldap_val('sudoUser', server.sudoers), [])
        except KeyError:
            self.assertEqual(True, True);
            
        server.sudoers.add(self.user)
        self.assertEqual(self.ldap_val('sudoUser', server.sudoers), [self.user.username])

        server.delete()
        try:
            self.ldap.fetch(dn='cn=AbSudoServer,{0}'.format(settings.SERVER_DN), scope=ldap.SCOPE_BASE, filters='(cn=*)')
            self.assertEqual(True, False)
        except ldap.NO_SUCH_OBJECT:
            self.assertEquals(True, True)

    def test_save_m2m_changes_exception(self):
        name = 'Abe3'
        server_mock = Servers(name=name)
        server = self.save_safe(Servers, dict(name=name, description="Abradabradaa"), lookup=dict(name=name))
        self.cleanup.append(server)
        with patch('fum.common.signals.changes_m2m') as o:
            o.side_effect = ChaosException
            # changes_m2m wrapped in try/except
            #with self.assertNotRaises(ChaosException):
            server.users.add(self.user)
            self.assertEqual([k.name for k in server.users.all()], [self.user.name])
            self.assertEqual(self.ldap_val('uniqueMember', server.users), [self.user.get_dn()])

        self.assertEqual(o.call_count, 2) # TODO: magic number against code that is changing...

    def test_save_m2m_signal_exception(self):
        """ ChaosException should rollback transaction, and ensure nothing goes to LDAP """
        name = 'Abe4'
        with patch('fum.common.signals.ldap_m2m', autospec=True) as o:
            self.add_signal(m2m_changed, receiver=o, sender=Servers.users.through, dispatch_uid='test_mocked_handler_m2m')

            o.side_effect = ChaosException
            server_mock = Servers(name=name)
            server = self.save_safe(Servers, dict(name=name, description="Abradabradaa"), lookup=dict(name=name))
            self.cleanup.append(server)

            with self.assertRaises(ChaosException):
                server.users.add(self.user)
            self.assertEqual(list(server.users.all()), [])
            with self.assertRaises(KeyError):
                self.ldap_val('uniqueMember', server.users)
        self.assertEqual(o.call_count, 1)

    def test_save_m2m_signal_exception_on_delete(self):
        name = 'Abe5'
        server_mock = Servers(name=name)
        server = self.save_safe(Servers, dict(name=name, description="Abradabradaa"), lookup=dict(name=name))
        self.cleanup.append(server)
        server.users.add(self.user)
        with patch('fum.common.signals.ldap_m2m', autospec=True) as o:
            self.add_signal(m2m_changed, receiver=o, sender=Servers.users.through, dispatch_uid='test_mocked_handler_m2m_on_delete')

            o.side_effect = ChaosException
            with self.assertRaises(ChaosException):
                server.users.remove(self.user)
            self.assertEqual([k.name for k in server.users.all()], [self.user.name])
            self.assertEqual(self.ldap_val('uniqueMember', server.users), [self.user.get_dn()])
        self.assertEqual(o.call_count, 1)

    def test_ldap_down_before_db_save(self):
        oldval = copy.deepcopy(self.user.first_name)
        with patch('fum.models.LDAPModel.save', autospec=True) as o:
            o.side_effect = ldap.SERVER_DOWN

            user = Users.objects.get(pk=self.user.pk)
            user.first_name = 'Jooseppi'
            with self.assertRaises(ldap.SERVER_DOWN):
                user.save()
            self.assertEqual(Users.objects.get(pk=self.user.pk).first_name, oldval)
            self.assertEqual(self.ldap_val('givenName', self.user), [oldval])

    def test_ldap_down_after_db_save(self):
        oldval = copy.deepcopy(self.user.first_name)
        with patch('fum.ldap_helpers.LDAPBridge.save', autospec=True) as o:
            o.side_effect = ldap.SERVER_DOWN

            user = Users.objects.get(pk=self.user.pk)
            user.first_name = 'Jooseppi'
            with self.assertRaises(ldap.SERVER_DOWN):
                user.save()

            self.assertEqual(Users.objects.get(pk=self.user.pk).first_name, oldval)
            self.assertEqual(self.ldap_val('givenName', self.user), [oldval])

    @unittest.expectedFailure
    def test_ldap_down_after_db_and_ldap_save(self):
        oldval = copy.deepcopy(self.user.first_name)
        newval = 'Jooseppi'
        with patch('fum.ldap_helpers.LDAPBridge.for_testing') as o:
            o.side_effect = ChaosException
            user = Users.objects.get(pk=self.user.pk)
            user.first_name = copy.deepcopy(newval)
            with self.assertRaises(ChaosException):
                user.save()
            self.assertEqual(Users.objects.get(pk=self.user.pk).first_name, oldval)
            self.assertEqual(self.ldap_val('givenName', user), [oldval])

    def test_ldap_down_after_db_and_during_m2m_ldap_save(self):
        name = 'Hessu'
        with patch('fum.common.signals.ldap_m2m', autospec=True) as o:
            self.add_signal(m2m_changed, receiver=o, sender=Servers.users.through, dispatch_uid='test_mocked_handler_m2m_failure')
            o.side_effect = ldap.SERVER_DOWN
            server_mock = Servers(name=name)
            server = self.save_safe(Servers, dict(name=name, description="Abradabradaa"), lookup=dict(name=name))
            self.cleanup.append(server)
            with self.assertRaises(ldap.SERVER_DOWN):
                server.users.add(self.user)
            self.assertEqual(list(server.users.all()), [])
            with self.assertRaises(KeyError):
                self.ldap_val('uniqueMember', server.users)
        self.assertEqual(o.call_count, 1)

    def test_ldap_timeout_after_db_and_during_m2m_ldap_save(self):
        name = 'Hessu'
        with patch('fum.common.signals.ldap_m2m', autospec=True) as o:
            self.add_signal(m2m_changed, receiver=o, sender=Servers.users.through, dispatch_uid='test_mocked_handler_m2m_timeout_failure')
            o.side_effect = ldap.TIMEOUT
            server_mock = Servers(name=name)
            server = self.save_safe(Servers, dict(name=name, description="Abradabradaa"), lookup=dict(name=name))
            self.cleanup.append(server)
            with self.assertRaises(ldap.TIMEOUT):
                server.users.add(self.user)
            self.assertEqual(list(server.users.all()), [])
            with self.assertRaises(KeyError):
                self.ldap_val('uniqueMember', server.users)
        self.assertEqual(o.call_count, 1)

    def test_value_in_ldap_not_in_db_will_overwite_ldap(self):
        name = 'Nightmare'
        data = dict(name=name, description="Abradabradaa")
        server = Servers(**data)

        new_attrs = {}
        new_attrs['objectClass'] = copy.deepcopy(server.ldap_object_classes)
        gu_id = 259
        new_attrs[server.ldap_id_number_field] = "%d"%gu_id
        new_attrs.update(data)
        del new_attrs['name']

        new_attrs['objectClass'].remove('sambaGroupMapping')
        mlist = modlist.addModlist(new_attrs)
        try:
            server.ldap.create_raw(server.get_dn(), mlist)
        except ldap.ALREADY_EXISTS, e:
            print e # no tearDown for this

        server = self.save_safe(Servers, data, lookup=dict(name=name))
        self.assertTrue(Servers.objects.get(name=name))

        server.description = 'Wonderland'
        server.save()

        self.assertEqual(self.ldap_val('description', server)[0], Servers.objects.get(name=name).description)

    def test_m2m_value_in_ldap_not_in_db_will_overwite_ldap(self):
        name = 'Nightmare2'
        data = dict(name=name, description="Abradabradaa")
        server = Servers(**data)

        new_attrs = {}
        new_attrs['objectClass'] = copy.deepcopy(server.ldap_object_classes)
        gu_id = 259
        new_attrs[server.ldap_id_number_field] = "%d"%gu_id
        new_attrs.update(data)
        del new_attrs['name']

        new_attrs['objectClass'].remove('sambaGroupMapping')
        mlist = modlist.addModlist(new_attrs)
        try:
            server.ldap.create_raw(server.get_dn(), mlist)
        except ldap.ALREADY_EXISTS, e:
            print e # no tearDown for this

        server = self.save_safe(Servers, data, lookup=dict(name=name))
        self.assertTrue(Servers.objects.get(name=name))

        # add related user to LDAP
        mlist = [(0, 'uniqueMember', ['uid=testuser,{0}'.format(settings.USER_DN)])]
        try:
            server.ldap.save_ext_raw(server.get_dn(), mlist)
        except ldap.TYPE_OR_VALUE_EXISTS, e:
            print e # no tearDown for this

        server.users.add(self.user)

        self.assertEqual([k.username for k in server.users.all()], [self.user.username])
        self.assertEqual([k.get_dn() for k in server.users.all()], self.ldap_val('uniqueMember', server.users))

        mlist = [(0, 'sudoUser', ['testuser'])]
        try:
            server.ldap.save_ext_raw(server.get_ldap_sudoers_dn(), mlist)
        except ldap.TYPE_OR_VALUE_EXISTS, e:
            print e # no tearDown for this

        server.sudoers.add(self.user)
        self.assertEqual([k.username for k in server.sudoers.all()], self.ldap_val('sudoUser', server.sudoers))

class ProjectTestCase(LdapTransactionSuite):
    def test_create_name(self):
        p = Projects()

        p.name = 'PFoo'
        setattr(settings, 'FUM_LAUNCH_DAY', datetime.datetime.now() - datetime.timedelta(days=5))
        with self.assertRaises(ValidationError):
            p.full_clean()

        p.name = 'foo'
        with self.assertRaises(ValidationError):
            p.full_clean()

        p.name = 'PfooBar'
        with self.assertRaises(ValidationError):
            p.full_clean()

        p.name = 'PFooBar'
        self.assertEqual(None, p.full_clean())

        p.name = 'P90Balloons'
        self.assertEqual(None, p.full_clean())

        p.name = 'PCompanyPHP'
        self.assertEqual(None, p.full_clean())

        p.name = 'PCOMPANYAndroid'
        with self.assertRaises(ValidationError):
            self.assertEqual(None, p.full_clean())

        p.name = 'P247entertainmentJukeW8'
        self.assertEqual(None, p.full_clean())


class SSHKeyTestCase(LdapTransactionSuite):

    valid_ssh_key = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC3uta/x/kAwbs2G7AOUQtRG7l1hjEws4mrvnTZmwICoGNi+TUwxerZgMbBBID7Kpza/ZSUqXpKX5gppRW9zECBsbJ+2D0ch/oVSZ408aUE6ePNzJilLA/2wtRct/bkHDZOVI+iwEEr1IunjceF+ZQxnylUv44C6SgZvrDj+38hz8z1Vf4BtW5jGOhHkddTadU7Nn4jQR3aFXMoheuu/vHYD2OyDJj/r6vh9x5ey8zFmwsGDtFCCzzLgcfPYfOdDxFIWhsopebnH3QHVcs/E0KqhocsEdFDRvcFgsDCKwmtHyZVAOKym2Pz9TfnEdGeb+eKrleZVsApFrGtSIfcf4pH user@host'
    valid_ssh_key_2 = 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDI86o9MlbA7NI/lXbWk7OSJw2bEfOAJsdkqrGmU1FVUZwCRupmx+VnelinyEUDCC5fwycTMcPAkUk990xogN8iH3aHZkfpun89091U+DyeLrfYPwP1lGo5ubGdPseAxJYZ4nbNQcBCGamtAwMeHl9UUfEoLFNE6GK62Yo9MGBNl28AeOX/NNz3WniMImr45x2kuL7E/pugnKcUCc2i1a+xxQdm4aqOzek/RYZ9pAwl8KeVipEUHpFZWsldLlXM28agzIrdxAVURc7rUJyz2PtF5vBrPTNDVhqX0tG3fgZ2uLlyWfc3a97gQrlgXKqM13hQ2lK0h5dPYWRe4WTFrmQn user2@host2'

    def get_ldap_ssh_keys(self, user=None):
        user = user or self.user
        data = self.user.ldap.op_search(user.get_dn(),
                ldap.SCOPE_BASE, 'uid=' + user.username,
                [SSHKey.LDAP_ATTR])
        data = data[0][1]
        if SSHKey.LDAP_ATTR in data:
            return data[SSHKey.LDAP_ATTR]
        return []

    def assert_ldap_ssh_key_count(self, count, user=None):
        self.assertEqual(len(self.get_ldap_ssh_keys(user)), count)

    def get_addsshkey_url(self, user=None):
        user = user or self.user
        return reverse('users-detail', args=[user.username]) + 'addsshkey/'

    def get_deletesshkey_url(self, user=None):
        user = user or self.user
        return reverse('users-detail', args=[user.username]) + 'deletesshkey/'

    def test_key_validity(self):
        self.assert_ldap_ssh_key_count(0)
        add_url = self.get_addsshkey_url()
        delete_url = self.get_deletesshkey_url()
        with self.assertRaises(sshpubkeys.InvalidKeyException):
            self.client.post(add_url,
                {'title': 'bad key', 'key': 'invalid string'}, format='json')

        resp = self.client.post(add_url,
            {'title': 'my key', 'key': self.valid_ssh_key}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assert_ldap_ssh_key_count(1)

        resp = self.client.post(add_url,
            {'title': 'my key 2', 'key': self.valid_ssh_key_2}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assert_ldap_ssh_key_count(2)

        resp = self.client.post(delete_url, {'fingerprint':
            SSHKey.objects.filter(user=self.user)[0].fingerprint},
            format='json', HTTP_X_HTTP_METHOD_OVERRIDE='DELETE')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assert_ldap_ssh_key_count(1)

    def test_equal_fingerprints(self):
        self.assert_ldap_ssh_key_count(0)
        url = self.get_addsshkey_url()

        resp = self.client.post(url,
            {'title': 'k1', 'key': self.valid_ssh_key}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        with self.assertRaises(ValidationError):
            # key with the same fingerprint
            resp = self.client.post(url,
                {'title': 'k2', 'key': self.valid_ssh_key + '2'}, format='json')

    def test_transaction(self):
        """
        Ensure no key is in the FUM DB if there's an error adding it to LDAP.
        """
        self.assert_ldap_ssh_key_count(0)
        url = self.get_addsshkey_url()

        def mocked(*args, **kwargs):
            raise Exception('mock')
        original = PoolLDAPBridge.op_modify
        try:
            PoolLDAPBridge.op_modify = mocked

            with self.assertRaises(Exception):
                resp = self.client.post(url,
                    {'title': 'k1', 'key': self.valid_ssh_key}, format='json')
        finally:
            PoolLDAPBridge.op_modify = original
        self.assert_ldap_ssh_key_count(0)
        self.assertEqual(SSHKey.objects.filter(user=self.user).count(), 0)

    def test_permissions(self):
        """
        Only sudo users can set or delete other users' ssh keys.
        """
        self.assert_ldap_ssh_key_count(0)
        add_url = self.get_addsshkey_url()
        delete_url = self.get_deletesshkey_url()

        resp = self.client.post(add_url,
            {'title': 'my key', 'key': self.valid_ssh_key}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assert_ldap_ssh_key_count(1)

        pw = random_ldap_password()
        other_dj_user, other_user = self.create_user('test_perm_user',
                password=pw)
        self.assertTrue(self.client.login(username=other_user.username,
            password=pw))

        # normal users can't add or delete other users' keys

        resp = self.client.post(add_url,
            {'title': 'my key', 'key': self.valid_ssh_key_2}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_ldap_ssh_key_count(1)

        resp = self.client.post(delete_url, {'fingerprint':
            SSHKey.objects.get(user=self.user).fingerprint},
            format='json', HTTP_X_HTTP_METHOD_OVERRIDE='DELETE')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_ldap_ssh_key_count(1)

        # superusers can add and delete others' ssh keys

        # add to TeamIT
        g = self.save_safe(Groups,
                kw=dict(name=settings.IT_TEAM),
                lookup=dict(name=settings.IT_TEAM))
        try:
            g.users.add(other_user)
        except ldap.TYPE_OR_VALUE_EXISTS, e: # live LDAP not cleaned
            pass
        response = self.client.post('/sudo/', {'password': pw},
                HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEquals(response.status_code, status.HTTP_200_OK)

        resp = self.client.post(add_url,
            {'title': 'my key', 'key': self.valid_ssh_key_2}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assert_ldap_ssh_key_count(2)

        for ssh_key in SSHKey.objects.filter(user=self.user):
            resp = self.client.post(delete_url,
                    {'fingerprint': ssh_key.fingerprint},
                    format='json', HTTP_X_HTTP_METHOD_OVERRIDE='DELETE')
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.assert_ldap_ssh_key_count(0)
