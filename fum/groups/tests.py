"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from fum.models import Groups, Users

from mockldap import MockLdap
from fum.common.ldap_test_suite import LdapSuite

class GroupsTestCase(LdapSuite):

    def setUp(self):
        super(GroupsTestCase, self).setUp()
        self.gx_name = "TestGroup7"
        self.gx = Groups.objects.create(name=self.gx_name, description="This is a test group")
        self.u1 = Users.objects.create(first_name="Teemu", last_name="Testari", username="ttes9", google_status=Users.ACTIVEPERSON)
        self.u2 = Users.objects.create(first_name="Teemu2", last_name="Testari2", username="ttes8", google_status=Users.ACTIVEPERSON)

    def tearDown(self):
        self.gx.delete()
        self.u1.delete()
        self.u2.delete()
        super(GroupsTestCase, self).tearDown()
    
    def test_adding_group(self):
        self.assertEqual(len(Groups.objects.filter(name=self.gx_name)), 1)
        self.assertEqual(unicode(self.gx), self.gx_name)

    def test_adding_members(self):

        self.gx.users.add(self.u1)
        self.assertEqual(len(self.gx.users.all()), 1)
        
        self.gx.users.add(self.u2)
        self.assertEqual(len(self.gx.users.all()), 2)

        self.gx.users.remove(self.u1)
        self.gx.users.remove(self.u2)
        

