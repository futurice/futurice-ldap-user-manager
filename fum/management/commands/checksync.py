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
from pprint import pprint as pp

from fum.models import Users, Groups, Projects, Servers

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check DB<>LDAP sync'

    def entries_with_id(self, results, newpk, key):
        matches = []
        for k in results:
            pk = k[1].get(key, None)
            if not pk:
                continue
            pk = pk[0]
            if int(newpk)==int(pk):
                matches.append(k)
        return matches

    def sync(self, matches):
        for instance, fields in matches.iteritems():
            for field in fields:
                curval = getattr(instance, field)
                l = instance.ldap
                mlist = l.get_modify_modlist(l.as_ldap_value(field, curval), force_update=True)
                l.op_modify(l.dn, mlist)

    def deep(self, queryset, exclude=[]):
        M = {'matches':{},'exclusions':{}}
        def compare(instance,dbval,ldap,ldapval):
            lval = ldap.get(ldapval, [''])
            ival = getattr(instance, mf)
            ival = unicode(ival).encode('utf-8') if (ival is not None) else ''
            return ival==lval[0]
        def store(instance, key):
            slot = 'matches'
            if key in exclude:
                slot = 'exclusions'
            M[slot].setdefault(instance, [])
            M[slot][instance].append(key)

        for instance in queryset:
            ul = instance.lval()
            for mf,lf in instance.ldap_fields.iteritems():
                if isinstance(lf, list):
                    for ldap_attr in lf:
                        if not compare(instance, mf, ul, ldap_attr):
                            store(instance, mf)
                else:
                    if not compare(instance, mf, ul, lf):
                        store(instance, mf)
        return M

    def roam(self, results, key):
        print "----------------------"
        duplicate = []
        broken = []
        ids = set()
        for k in results:
            pk = k[1].get(key, None)
            if not pk:
                broken.append(k)
                continue
            # skip ou=Luola (obsolete)
            if "ou=Luola" in k[0]:
                return
            pk = pk[0]
            if pk not in ids:
                ids.add(pk)
            else:
                duplicate.append(k)
        for k in duplicate:
            pp(self.entries_with_id(results, k[1][key][0], key))
        return dict(duplicate=duplicate, broken=broken)

    def exists_in_db(self, results, field='name'):
        result = dict(yes=[], no=[], error=[])
        for k in results:
            hostpath = k[0]
            cn = [j for i,j in tuple([h.split('=') for h in hostpath.split(',')]) if i in ['cn','uid']]
            model = self.get_ldap_group_model(hostpath)
            if cn:
                try:
                    r = model.objects.get(**{field: cn[0]})
                except Exception, e:
                    result['no'].append(k)
            else:
                result['error'].append(k)
        return result

    def get_ldap_group_model(self, cn):
        if "ou=Groups" in cn:
            if "ou=Projects" in cn:
                model = Projects
            elif "ou=Hosts" in cn:
                model = Servers
            else:
                model = Groups
        if "ou=People" in cn:
            model = Users
        if not model:
            raise Exception("No model found", cn)
        return model


    def handle(self, *args, **options):
        print "Data in FUM, that is *NOT* in LDAP"
        missing = {'fum-ldap': {}, 'ldap-fum': {}}
        for h in [Users, Groups, Projects, Servers]:
            missing['fum-ldap'].setdefault(h, [])
            missing['ldap-fum'].setdefault(h, [])
            for i in h.objects.all().order_by('pk'):
                try:
                    i.lval()
                except Exception, e:
                    missing['fum-ldap'][h].append(i)
        pp(missing['fum-ldap'])

        print "========================="
        print "Test gidNumber existence, uniqueness"
        gids = {}
        u = Users()
        # gidNumber = 2000 for all, uidNumber is unique
        results = u.ldap.fetch(u.ldap_base_dn, scope=ldap.SCOPE_SUBTREE, filters=u.ldap_filter, attrs=['gidNumber','uidNumber'])
        rs = self.roam(results, 'uidNumber')
        gids[Users] = rs
        missing['ldap-fum'][Users] = self.exists_in_db(results, field='username')

        for o in [Groups]: # Groups holds ou=Hosts, ou=Projects within
            print o
            u = o()
            results = u.ldap.fetch(u.ldap_base_dn, scope=ldap.SCOPE_SUBTREE, filters=u.ldap_filter, attrs=['gidNumber'])
            rs = self.roam(results, 'gidNumber')
            gids[o] = rs
            missing['ldap-fum'][o] = self.exists_in_db(results, field='name')
        pp(gids)

        print "========================="
        print "Data in LDAP, that is *NOT* in FUM"
        pp(missing['ldap-fum'])
