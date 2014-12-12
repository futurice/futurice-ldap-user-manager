from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.template.loader import get_template
from django.template import Context
from django.forms import EmailField
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_unicode

import ldap
import sys
import pytz
from datetime import datetime
from optparse import make_option
import logging

from fum.models import *

import sys
import ldap
import pytz
from datetime import datetime
from fum.models import *
from django.conf import settings

from django.forms import EmailField
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_unicode

from fum.ldap_helpers import *
from ldap import modlist

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Teams migration'
    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
            action='store_true',
            dest='dry',
            default=False,
            help='Teams migration'),
        )

    def handle(self, *args, **options):
        # COPY TEAMS UNDER GROUPS

        def isEmailAddressValid(email):
            try:
                EmailField().clean(email)
            except ValidationError:
                return False
            return True

        def val(v, member):
            if member not in v:
                return None
            result = v[member][0]
            result = smart_unicode(result)
            return result

        # LDAP connection
        ldap_server = settings.MIGRATION['LDAP']['uri']
        dn = settings.MIGRATION['LDAP']['bind_dn']
        pw = settings.MIGRATION['LDAP']['bind_pwd']

        # LDAP groups
        group_base_dn = settings.TEAM_DN
        group_filter = "(objectclass=posixGroup)"
        group_attrs = ['uniqueMember','description','mail','cn','gidNumber','editpermission','proxyaddress','sambaGroupType','sambaSID',]

        ldap_object_classes = ['top', 'posixGroup', 'groupOfUniqueNames', 'mailRecipient', 'google', 'sambaGroupMapping']

        # Ignore certificates
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, 0)

        con = ldap.initialize(ldap_server)
        con.start_tls_s()
        con.simple_bind_s(dn,pw)

        conn_test = open_ldap()
        group = Groups()

        res = con.search_s(group_base_dn, ldap.SCOPE_SUBTREE, group_filter, group_attrs)

        # ou=Teams,ou=Groups,dc... => ou=Groups,dc..., with new gidNumber
        for u in res:
            dn = str(u[0])
            dn = dn.replace('ou=Teams,','')
            v = u[1]
            print dn
            new_attrs = {}
            new_attrs['objectClass'] = ldap_object_classes
            v.update(new_attrs)
            del v['gidNumber'] # Teams range is 3000+, Groups is [2000,3000]
            # new ID done in datamigrate-phase, fetch it
            migrated_team = Groups.objects.get(name=val(v,'cn'))
            gu_id = migrated_team.pk
            v.update({'gidNumber': [str(gu_id)],
                    'sambaSID':'%s-%s' % (settings.SAMBASID_BASE, gu_id * 2 + 1001)})
            mlist = modlist.addModlist(v)
            try:
                conn_test.add_s(dn, mlist)
            except ldap.ALREADY_EXISTS, e:
                # TODO: get, and update Sambda-fields..
                print e

        print "DONE: Teams copied under Groups in LDAP"
