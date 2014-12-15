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
import pytz
from datetime import datetime
from optparse import make_option
import logging

from fum.models import *

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Labeled URI remove'
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
        group_attrs = ['labeledURI','cn','objectClass']

        # get groups from ldap
        ldap_groups = con.search_s(group_base_dn, ldap.SCOPE_SUBTREE, group_filter, group_attrs)

        print "Removing labeledURI and objectClass=labeledURIObject from groups"

        for g in ldap_groups:
            attrs = [(ldap.MOD_DELETE, 'labeledURI', None),(ldap.MOD_DELETE, 'objectClass', 'labeledURIObject')]
            for mod_attrs in attrs:
                try:
                    con.modify_s(g[0], [mod_attrs])
                    print "removed "+str(mod_attrs)+" from "+str(g[1]['cn'])
                except:
                    print "no hit for "+str(mod_attrs)+" let's continue "+str(g[1]['cn'])
                    pass

        con.unbind()
        print "Done"
