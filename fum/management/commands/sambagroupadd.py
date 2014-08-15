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
    help = 'Samba Group Add'
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
        group_base_dn = settings.GROUP_DN
        group_filter = "(objectclass=posixGroup)"
        group_attrs = ['cn','objectClass', 'gidNumber']

        # get groups from ldap
        ldap_groups = con.search_s(group_base_dn, ldap.SCOPE_SUBTREE, group_filter, group_attrs)

        print "Adding sambaSID, sambaGroupType and objectClass=sambaGroupMapping to groups"

        for g in ldap_groups:
            attrs = [(ldap.MOD_ADD, 'objectClass', 'sambaGroupMapping'),(ldap.MOD_ADD, 'sambaSID', 'S-1-5-21-1049098856-3271850987-3507249052-%s' % (int(g[1]['gidNumber'][0]) * 2 + 1001)),(ldap.MOD_ADD, 'sambaGroupType', '2')]
            try:
                con.modify_s(g[0], attrs)
                print "added "+str(attrs)+" from "+str(g[1]['cn'])
            except Exception, e:
                print e
                print "no hit for "+str(attrs)+" let's continue "+str(g[1]['cn'])
                pass

        con.unbind()
        print "Done"
