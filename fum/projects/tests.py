# encoding=utf8
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

import datetime, copy
from pprint import pprint as pp

from fum.models import Users, EMails, Projects, EPOCH, Groups, Projects
from fum.common.ldap_test_suite import LdapSuite, LdapTransactionSuite
from fum.projects.util import name_to_email

class ProjectTest(LdapTransactionSuite):

    def test_create(self):
        p = Projects(name='PSoFArsogood')
        p.save()
        self.assertTrue(EMails.objects.get(address=name_to_email(p.name)))
        self.assertTrue(EMails.objects.filter(
            object_id=p.pk,
            content_type=ContentType.objects.get_for_model(p)).count(), 1)
        self.assertTrue(p.pk is not None)
        p.description = 'So Far So Good'
        p.save()
        self.assertTrue(EMails.objects.get(address=name_to_email(p.name)))
        self.assertTrue(EMails.objects.filter(
            object_id=p.pk,
            content_type=ContentType.objects.get_for_model(p)).count(), 1)

        p = Projects(name='PSo')
        with self.assertRaises(ValidationError):
            p.save()

    def test_email_from_name(self):
        self.assertEqual(name_to_email('PNokiaMaps'), 'project-nokia-maps@futurice.com')
        self.assertEqual(name_to_email('PSoFArsogood'), 'project-so-farsogood@futurice.com')
