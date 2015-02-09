# encoding=utf8
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils.timezone import now

from fum.models import Users, EMails, Projects, EPOCH, Groups, Servers, EPOCH, calculate_password_valid_days
from fum.common.ldap_test_suite import LdapSuite, LdapTransactionSuite
from fum.common.util import random_ldap_password
import base64, json

import ldap
import datetime, copy
from fum.ldap_helpers import test_user_ldap
from pprint import pprint as pp
from rest_framework import status
from mock import patch, MagicMock, PropertyMock
from dateutil.relativedelta import relativedelta

import sys
from StringIO import StringIO

from fum.management.commands.remind import Command as RemindCommand
from fum.management.commands.suspendaccounts import Command as SuspendAccountCommand

class UserTest(LdapTransactionSuite):

    def test_status(self):
        u = self.save_safe(Users,
                kw=dict(first_name="Who", last_name="AmI", username='whoami', google_status=Users.ACTIVEPERSON),
                lookup=dict(username='whoami'))
        uf = lambda instance: Users.objects.get(username=instance.username)
        self.assertEqual(u.get_status(), Users.USER_ACTIVE)

        g = self.save_safe(Groups,
                kw=dict(name='Elysium', description="Elysium"),
                lookup=dict(name='Elysium'))
        g.users.add(u)
        self.assertTrue(u.in_group(g))
        self.assertEqual(uf(u).lval().get('shadowMax'), [str(calculate_password_valid_days())])

        u.set_disabled()
        self.assertEqual(u.get_status(), Users.USER_DISABLED)
        self.assertTrue(u.in_group(g))
        self.assertEqual(uf(u).lval().get('shadowMax'), ['0'])

        u.set_deleted()
        self.assertFalse(u.in_group(g))
        self.assertEqual(u.get_status(), Users.USER_DELETED)
        self.assertEqual(uf(u).google_status, Users.DELETED)
        self.assertEqual(uf(u).lval().get('shadowMax'), ['0'])

        u.set_active()
        self.assertEqual(u.get_status(), Users.USER_ACTIVE)
        self.assertEqual(uf(u).google_status, Users.DELETED)
        self.assertEqual(uf(u).lval().get('shadowMax'), ['0'])

    def test_server_user_sudo(self):
        server = Servers.objects.create(name="TestServletti", description="description")
        u = self.save_safe(Users,
                kw=dict(first_name="Teemu", last_name="Testaaj", username='tavis', google_status=Users.ACTIVEPERSON),
                lookup=dict(username='tavis'))
        u2 = self.save_safe(Users,
                kw=dict(first_name="Jarkko", last_name="Testaaja", username='tavit', google_status=Users.ACTIVEPERSON),
                lookup=dict(username='tavit'))
        u3 = self.save_safe(Users,
                kw=dict(first_name="Heikki", last_name="Testaaja", username='taviu', google_status=Users.ACTIVEPERSON),
                lookup=dict(username='taviu'))
        server.users.add(u)
        server.users.add(u2)
        server.users.add(u3)
        server.sudoers.add(u)
        server.sudoers.add(u2)
        server.sudoers.add(u3)
        server.users.remove(u2)
        self.assertTrue([k in server.users.all() for k in [u,u3]])
        self.assertTrue([k in server.sudoers.all() for k in [u,u3]])

    def test_lastname_only(self):
        last_name = "CorporateLevel"
        u3 = self.save_safe(Users,
                kw=dict(last_name=last_name, username='corlev', google_status=Users.ACTIVEPERSON),
                lookup=dict(username='corlev'))
        self.assertEquals(u3.lval().get('cn'), [last_name])

    def test_default_values_like_google_status_saved_into_ldap(self):
        u = self.save_safe(Users,
                kw=dict(first_name="Roope", last_name="Testaaja", username='crote'),
                lookup=dict(username='crote'))
        self.assertEqual(u.lval().get('googleStatus'), [Users.UNDEFINED])
        u.google_status = Users.ACTIVEPERSON
        u.save()
        self.assertEqual(u.lval().get('googleStatus'), [Users.ACTIVEPERSON])
        u.google_status = Users.UNDEFINED
        u.save()
        self.assertEqual(u.lval().get('googleStatus'), [Users.UNDEFINED])

        # samba
        self.assertEqual(u.lval().get('sambaPwdLastSet'), [Users.SAMBA_PWD_EXPIRY_TIMESTAMP])

        u2 = self.save_safe(Users,
                kw=dict(first_name="Riina", last_name="Testaaja", username='crina', google_status=Users.ACTIVEPERSON),
                lookup=dict(username='crina'))
        self.assertEqual(u2.lval().get('googleStatus'), [Users.ACTIVEPERSON])
        u2.google_status = Users.UNDEFINED
        u2.save()
        self.assertEqual(u2.lval().get('googleStatus'), [Users.UNDEFINED])
        self.assertEqual(Users.objects.get(username=u2.username).google_status, Users.UNDEFINED)

        changes = {'google_status': {'new': u.google_status, 'old': u.google_status}}
        u2.save(changes=changes)
        self.assertEqual(u2.lval().get('googleStatus'), [Users.UNDEFINED])
        self.assertEqual(Users.objects.get(username=u2.username).google_status, Users.UNDEFINED)

        changes = {'google_status': {'new': Users.ACTIVEPERSON, 'old': u.google_status}}
        u2.save(changes=changes)
        self.assertEqual(u2.lval().get('googleStatus'), [Users.ACTIVEPERSON])
        self.assertEqual(Users.objects.get(username=u2.username).google_status, Users.ACTIVEPERSON)

    def test_user_email(self):
        self.assertEqual(self.user.email.all().count(), 0)
        self.user.email.add(EMails(address='pentti@futurice.com', content_object=self.user))
        self.assertEqual(self.user.email.all().count(), 1)
        self.assertEqual(self.ldap_val('mail', self.user), ['pentti@futurice.com'])
        self.user.title = 'something else'
        self.user.save()
        self.assertEqual(self.user.email.all().count(), 1)
        self.assertEqual(self.ldap_val('mail', self.user), ['pentti@futurice.com'])

        self.user.email.add(EMails(address='pentti2@futurice.com', content_object=self.user))
        self.assertEqual(self.user.email.all().count(), 1)
        self.assertEqual(self.user.email.all()[0].address, 'pentti2@futurice.com')
        self.assertEqual(self.ldap_val('mail', self.user), ['pentti2@futurice.com'])
        self.user.email = [] # unsetting email in API might be problematic :knock wood-not so
        self.assertEqual(self.user.email.all().count(), 0)

    def test_user_hr_number(self):
        hr_number = "1234"
        self.user.hr_number = hr_number
        self.user.save()
        self.assertEqual(self.user.hr_number, hr_number)
        response = self.client.post("/api/users/%s/"%self.user.username,
            data={"hr_number": "jee",},
            HTTP_X_HTTP_METHOD_OVERRIDE='PATCH',)
        rs = json.loads(response.content)
        self.assertEqual(rs['hr_number'], "jee")

    def test_user_title(self):
        self.user.title = 'Hulabaloo'
        self.user.save()

    def test_user_editing(self):
        self.user.phone1 = "+358 1234 3456"
        self.user.save()
        self.assertEqual(Users.objects.get(username=self.USERNAME).phone1, "+35812343456")

        self.user.active_in_planmill = True
        self.user.save()
        self.assertEqual(Users.objects.get(username=self.USERNAME).active_in_planmill, True)

        self.user.first_name=u'Täämu'
        self.user.save()
        self.assertEqual(Users.objects.get(username=self.USERNAME).first_name, u'Täämu')

        email = EMails(address="testi.teemu@futurice.com", content_object=self.user)
        email.save()
        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "testi.teemu@futurice.com")

    def test_change_password(self):
        self.assertNotEqual(self.user.password, '')
        self.assertEqual(self.user.get_changes('ldap'), {})
        u = Users()
        self.assertTrue('password' not in u.get_changes())
        self.assertTrue('created' in u.get_changes())
        u_values = u.get_changes('ldap').keys()
        self.assertTrue(all(k in u.ldap_only_fields.keys() for k in u_values))

        current_password = self.ldap_val('userPassword', self.user)
        current_google_password = self.ldap_val('googlePassword', self.user)
        current_samba_password = self.ldap_val('sambaNTPassword', self.user)


        self.user.shadow_last_change = (now() - datetime.timedelta(days=5) - EPOCH).days
        self.user.save()
        shadow_last_change = copy.deepcopy(self.user.shadow_last_change)

        password = random_ldap_password()
        self.user.set_ldap_password(password)
        self.assertEqual(self.user.get_changes('ldap'), {})
        self.assertNotEqual(self.ldap_val('userPassword', self.user), current_password)
        self.assertNotEqual(self.ldap_val('googlePassword', self.user), current_google_password)
        self.assertNotEqual(self.ldap_val('sambaNTPassword', self.user), current_samba_password)
        self.assertNotEqual(self.user.password, '')
        self.assertNotEqual(self.user.shadow_last_change, shadow_last_change)

    def test_leaving_planmill_not_allowed(self):
        u = self.save_safe(Users,
                kw=dict(first_name="No", last_name="Exit", username='noex', google_status=Users.ACTIVEPERSON),
                lookup=dict(username='noex'))
        self.assertEqual(u.active_in_planmill, Users.PLANMILL_DISABLED)
        u.active_in_planmill = Users.PLANMILL_ACTIVE
        u.save()
        u.active_in_planmill = Users.PLANMILL_DISABLED
        with self.assertRaises(ValidationError):
            u.save()
        self.assertEqual(Users.objects.get(username='noex').active_in_planmill, Users.PLANMILL_ACTIVE)

        u.active_in_planmill = Users.PLANMILL_INACTIVE
        u.save()

        u.active_in_planmill = Users.PLANMILL_DISABLED
        with self.assertRaises(ValidationError):
            u.save()
        self.assertEqual(Users.objects.get(username='noex').active_in_planmill, Users.PLANMILL_INACTIVE)

        u.active_in_planmill = Users.PLANMILL_ACTIVE
        u.save()


    def test_bad_password(self):
        # TODO: ldap-environment (+mock) that fails when using bad password
        password='bad'
        u = self.save_safe(Users,
                kw=dict(first_name="Bad", last_name="Password", username='bpas', google_status=Users.ACTIVEPERSON),
                lookup=dict(username='bpas'))
        with self.assertRaises(KeyError):
            self.assertEqual(self.ldap_val('userPassword', u), 'no_password_on_user_creation')
        if not settings.LDAP_MOCK:
            with self.assertRaises(ldap.CONSTRAINT_VIOLATION):
                u.set_ldap_password(password)

    def test_upload_portrait(self):
        with open('%s/fum/users/sample/futucare.png'%settings.PROJECT_ROOT) as fp:
            portrait = 'data:image/png;base64,'+base64.b64encode(fp.read())
            response = self.client.post("/api/users/%s/portrait/"%self.user.username, data={
                "portrait":portrait,
                "left":444,
                "top":0,
                "right":570,
                "bottom":189,
                })
            rs = json.loads(json.loads(response.content))
            self.assertTrue(rs['full'])

    def test_badge_crop_permissions(self):
        """
        Users can only change their own photo crop. Sudoers can chage others'.
        """
        # upload a portrait first, to be able to crop it for the badge
        with open('%s/fum/users/sample/futucare.png'%settings.PROJECT_ROOT) as fp:
            portrait = 'data:image/png;base64,'+base64.b64encode(fp.read())
            response = self.client.post("/api/users/%s/portrait/"%self.user.username, data={
                "portrait":portrait,
                "left":444,
                "top":0,
                "right":570,
                "bottom":189,
                })
            rs = json.loads(json.loads(response.content))
            self.assertTrue(rs['full'])
        # end portrait upload: copied from test_upload_portrait()

        def get_url(user=None):
            user = user or self.user
            return reverse('users-badgecrop', args=[user.username])

        url = get_url()
        payload = {'top': 0, 'left': 0, 'right': 20, 'bottom': 20}

        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        pw = random_ldap_password()
        other_dj_user, other_user = self.create_user('test_perm_user',
                password=pw)
        self.assertTrue(self.client.login(username=other_user.username,
            password=pw))

        # normal users can't change other users' badge crop

        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        # superusers can change others' badge crop

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

        resp = self.client.post(url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_user_m2m_groups(self):
        u = self.save_safe(Users,
                kw=dict(first_name="Bad",
                    last_name="Boy",
                    username='badboy',
                    google_status=Users.ACTIVEPERSON),
                lookup=dict(username='badboy'))
        gfu = self.save_safe(Groups,
                kw=dict(name='Futurice', description="FG"),
                lookup=dict(name='Futurice'))
        git = self.save_safe(Groups,
                kw=dict(name='TeamIT', description="TI"),
                lookup=dict(name='TeamIT'))
        gfu.users.add(u) # operations in "shell" have no restrictions

class ChangesTest(LdapSuite):

    def test_change_phone(self):
        self.user.phone1 = "+358 1234 3456"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).phone1, "+35812343456")

        self.user.phone1 = "00 358 1234"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).phone1, "+3581234")

        self.user.phone2 = "+358 1234 3456"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).phone2, "+35812343456")

        self.user.phone2 = "00 358 1234"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).phone2, "+3581234")


    def test_change_skype(self):
        self.user.skype = "testskype"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).skype, "testskype")

        self.user.skype = "testskype2"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).skype, "testskype2")

        self.user.skype = "testskype3"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).skype, "testskype3")

        self.user.skype = ""
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).skype, "")

    def test_change_skype(self):
        self.user.skype = "testskype"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).skype, "testskype")

        self.user.skype = "testskype2"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).skype, "testskype2")

        self.user.skype = "testskype3"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).skype, "testskype3")

        self.user.skype = ""
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).skype, "")

    def test_change_name(self):
        self.user.first_name = "Firstnametest"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).first_name, "Firstnametest")

        self.user.last_name = "Lastnametest"
        self.user.save()

        self.assertEqual(Users.objects.get(username=self.USERNAME).last_name, "Lastnametest")

    def test_change_email(self):
        email = EMails(address="testi.teemu@futurice.com", content_object=self.user)
        email.save()
        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "testi.teemu@futurice.com")

        email.address = ""
        email.save()
        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "")

        email.address = "testi2@futurice.com"
        email.save()
        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "testi2@futurice.com")

    def test_check_pwd(self):
        self.assertFalse(test_user_ldap(self.user.username,'WRONGPWD'))
        



class ValidationTest(LdapSuite):

    def test_phone_valid(self):
        self.user.phone1 = "+358 1234 3456"
        self.user.save()

        try:
            self.user.phone1 = "notvalid"
            self.user.save()
        except:
            pass
        try:
            self.user.phone1 = "358 1234 3456"
            self.user.save()
        except:
            pass
        try:
            self.user.phone1 = "00a358 1234 3456"
            self.user.save()
        except:
            pass

        try:
            self.user.phone1 = "00 358 1234 3456"
            self.user.save()
        except:
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).phone1, "+35812343456")

        try:
            self.user.phone2 = "notvalid"
            self.user.save()
        except:
            pass
        try:
            self.user.phone2 = "358 1234 3456"
            self.user.save()
        except:
            pass
        try:
            self.user.phone2 = "00a358 1234 3456"
            self.user.save()
        except:
            pass

        try:
            self.user.phone2 = "00 358 1234 3456"
            self.user.save()
        except:
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).phone2, "+35812343456")

    def test_skype_valid(self):
        self.user.skype = "test.user"
        self.user.save()

        try:
            self.user.skype = "#notvalid"
            self.user.save()
        except:
            pass
        try:
            self.user.skype = "not valid"
            self.user.save()
        except:
            pass
        try:
            self.user.skype = "is-valid"
            self.user.save()
        except:
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).skype, "is-valid")


    def test_email_valid_via_email(self):
        email = EMails.objects.create(address="valid.email@futurice.com", content_type=ContentType.objects.get_for_model(self.user), object_id=self.user.pk)

        try:
            email.address = "notvalid@futurice"
            email.save()
        except Exception, e:
            print e
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "valid.email@futurice.com")

        try:
            email.address = "not valid mail"
            email.save()
        except Exception, e:
            print e
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "valid.email@futurice.com")

        try:
            email.address = "valid@mailproviderx.com"
            email.save()
        except Exception, e:
            print e
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "valid@mailproviderx.com")

        try:
            email.address = ""
            email.save()
        except Exception, e:
            print e
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "")

    def test_email_valid_via_user(self):
        email = EMails.objects.create(address="valid.email@futurice.com", content_type=ContentType.objects.get_for_model(self.user), object_id=self.user.pk)

        try:
            mail = "notvalid@futurice"
            self.user.email.add(EMails(address=mail, content_object=self.user))
        except Exception, e:
            print e
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "valid.email@futurice.com")

        try:
            mail = "not valid mail"
            self.user.email.add(EMails(address=mail, content_object=self.user))
        except Exception, e:
            print e
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "valid.email@futurice.com")

        try:
            mail = "valid@mailproviderx.com"
            self.user.email.add(EMails(address=mail, content_object=self.user))
        except Exception, e:
            print e
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "valid@mailproviderx.com")

        try:
            mail = ""
            self.user.email.add(EMails(address=mail, content_object=self.user))
        except Exception, e:
            print e
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email().address, "")

        try:
            self.user.email.clear()
        except Exception, e:
            print e
            pass

        self.assertEqual(Users.objects.get(username=self.USERNAME).get_email(), None)

from django.core.management import call_command
class ReminderTestCase(LdapSuite):
    def setUp(self):
        super(ReminderTestCase, self).setUp()

    def tearDown(self):
        super(ReminderTestCase, self).tearDown()

    def test_remind_password(self):
        du1,u1 = self.create_user('amok')
        du2,u2 = self.create_user('amexpired')
        dtnow = now().replace(hour=0, minute=0, microsecond=0, second=00)
        u2.shadow_last_change = ((dtnow - datetime.timedelta(days=5)) - EPOCH).days - u1.shadow_max
        u2.save()
        u1.shadow_last_change = ((dtnow - datetime.timedelta(days=5)) - EPOCH).days - u1.shadow_max
        u1.save()
        u1.email.add(EMails(address='u1@futurice.com', content_object=u1))
        self.assertTrue( (dtnow-u1.password_expires_date).days, 5-1)

        with self.settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'):
            with patch('fum.management.commands.remind.send_mail') as o:
                c = RemindCommand()
                c.handle('password', dry=True, force=True)
                self.assertFalse(o.called)

        with self.settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'):
            with patch('fum.management.commands.remind.send_mail') as o:
                c = RemindCommand()
                c.handle('password', dry=False, force=True)
                self.assertTrue(o.called)

        self.assertTrue( u1 in [k[0] for k in c.emailed] )
        self.assertFalse( u2 in [k[0] for k in c.emailed] )

    def test_suspend_user(self):
        du1,u1 = self.create_user('amsuspended')
        dtnow = now().replace(hour=0, minute=0, microsecond=0, second=00)
        u1.shadow_last_change = ((dtnow - datetime.timedelta(days=5)) - EPOCH).days - u1.shadow_max
        u1.suspended_date = (dtnow - datetime.timedelta(days=5))
        u1.save()
        u1.email.add(EMails(address='u1@futurice.com', content_object=u1))

        with self.settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'):
            c = SuspendAccountCommand()
            c.handle('suspendaccounts', dry=True, force=True)

        u1a = Users.objects.get(username=u1.username)
        self.assertEqual( u1a.google_status, u1a.ACTIVEPERSON)

        with self.settings(EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'):
            c = SuspendAccountCommand()
            c.handle('suspendaccounts', dry=False, force=True)

        self.assertTrue( u1 in c.suspended )
        u1a = Users.objects.get(username=u1.username)
        self.assertTrue(u1a.shadow_last_change != u1.shadow_last_change)
        g,_ = Groups.objects.get_or_create(name="Disabled")
        self.assertTrue(u1a.in_group(g))
