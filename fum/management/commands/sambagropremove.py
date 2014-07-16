from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.template.loader import get_template
from django.template import Context
from django.forms import EmailField
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_unicode

import re
import ldap
import sys
import _mysql
import pytz
from datetime import datetime
from optparse import make_option
import logging

from fum.models import *

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Samba Group Remove'
    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
            action='store_true',
            dest='dry',
            default=False,
            help=''),
        )

    def handle(self, *args, **options):
        log.info("Running")
        # LDAP connection
        con = open_ldap()

        # LDAP groups
        group_base_dn = "ou=groups,dc=futurice,dc=com"
        group_filter = "(objectclass=posixGroup)"
        group_attrs = ['cn','objectClass', 'sambaSID', 'sambaGroupType', 'displayName']

        # get groups from ldap
        ldap_groups = con.search_s(group_base_dn, ldap.SCOPE_SUBTREE, group_filter, group_attrs)

        print "Removing sambaSID, sambaGroupType and objectClass=sambaGroupMapping from groups"

        for g in ldap_groups:
            object_classes = g[1]['objectClass']
            try:
                object_classes.remove('sambaGroupMapping')
            except:
                continue
            attrs = [(ldap.MOD_REPLACE, 'objectClass', object_classes),(ldap.MOD_DELETE, 'sambaSID', None),(ldap.MOD_DELETE, 'sambaGroupType', None)]
            if 'displayName' in g[1]:
                attrs.append((ldap.MOD_DELETE, 'displayName', None))
            try:
                con.modify_s(g[0], attrs)
                print "removed "+str(attrs)+" from "+str(g[1]['cn'])
            except Exception, e:
                print e
                print "no hit for "+str(attrs)+" let's continue "+str(g[1]['cn'])
                pass

        con.unbind()
        print "Done"
