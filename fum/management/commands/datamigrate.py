#encoding=utf8
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

def get_google_enum(status):
    ret = 0
    for t in Users.GOOGLE_STATUS_CHOICES:
        if t[1] == status:
            ret = t[0]
            break
    return ret

class Command(BaseCommand):
    help = 'Data migration'
    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
            action='store_true',
            dest='dry',
            default=False,
            help='Data migration'),
        )

    def handle(self, *args, **options):
        log.info("Running")
        cleanup_cruft = [
            'cn=PTestGroup,{0}'.format(settings.PROJECT_DN)
        ]
        instance = Groups()
        for dn in cleanup_cruft:
            try:
                instance.ldap.delete(dn=dn)
            except Exception, e:
                print e
        print "Disabling changes-socket"
        setattr(settings, 'CHANGES_SOCKET_ENABLED', False)
        print "Disabling LDAP sync"
        setattr(settings, 'LDAP_CLASS', 'fum.ldap_helpers.DummyLdap')
        print "Disabling Solr sync"
        setattr(settings, 'HAYSTACK_SIGNAL_PROCESSOR', 'haystack.signals.BaseSignalProcessor')
        print "Disable project naming validation"
        setattr(settings, 'ENFORCE_PROJECT_NAMING', False)

        def clean_email(email):
            if email is None or len(email) == 0 or 'undefined' in email: return None
            # remove whitespace
            return re.sub("\s+","", email)

        def isEmailAddressValid(email):
            try:
                EmailField().clean(email)
            except ValidationError:
                return False
            return True

        def val(v, member):
            if member not in v:
                return None
            if v[member] is None:
                return None
            result = v[member][0].strip()
            result = smart_unicode(result)
            return result

        # LDAP connection
        ldap_server = settings.MIGRATION['LDAP']['uri']
        dn = settings.MIGRATION['LDAP']['bind_dn']
        pw = settings.MIGRATION['LDAP']['bind_pwd']

        # LDAP users
        user_base_dn = settings.USER_DN
        user_filter = "(objectclass=person)"
        user_attrs = ['givenName','sn','uid','title','mail','telephoneNumber','mobile','googleStatus','sambaPwdMustChange','gidNumber','proxyaddress','uidnumber', 'shadowLastChange', 'shadowMax', 'physicalDeliveryOfficeName']

        # LDAP groups
        group_base_dn = settings.GROUP_DN
        group_filter = "(objectclass=posixGroup)"
        group_attrs = ['uniqueMember','description','mail','cn','gidNumber','editpermission','proxyaddress']

        # LDAP sudoers
        sudoer_base_dn = settings.COMPANY_DN
        sudoer_filter = "(objectclass=sudoRole)"
        sudoer_attrs = ['sudoUser','sudoHost','cn']

        # Old FUM MySQL connection
        mysql_server = settings.MIGRATION['MYSQL']['uri']
        mysql_port = settings.MIGRATION['MYSQL']['port']
        mysql_user = settings.MIGRATION['MYSQL']['user']
        mysql_pw = settings.MIGRATION['MYSQL']['pw']
        mysql_db = settings.MIGRATION['MYSQL']['db']

        # Local timezone
        tz = pytz.timezone('Europe/Helsinki')

        # open connections
        try:
            db = _mysql.connect(host=mysql_server,port=mysql_port,user=mysql_user,passwd=mysql_pw,db=mysql_db)
        except Exception, e:
            print e

        # Ignore certificates
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, 0)

        con = ldap.initialize(ldap_server)
        con.start_tls_s()
        con.simple_bind_s(dn,pw)

        # get users from ldap
        ldap_users = con.search_s(user_base_dn, ldap.SCOPE_SUBTREE, user_filter, user_attrs)

        print "Migrating users", len(ldap_users)

        # chew through the users
        for u in ldap_users:
            print u
            v = u[1]
            # get skype name from fum3 database
            try:
                db.query("select skype from node_extensions_extendeduser where rdn_value = '"+v['uid'][0]+"'")
                r = db.store_result()
                result = r.fetch_row()
                skype_name = None if len(result) < 1 else result[0][0]
            except Exception, e:
                skype_name = None
            user = Users(id=val(v,'uidNumber'),first_name=val(v,'givenName'),last_name=val(v,'sn'),username=val(v,'uid'),title=val(v,'title'),phone1=val(v,'telephoneNumber'),phone2=val(v,'mobile'),skype=skype_name,physical_office=val(v,'physicalDeliveryOfficeName'),google_status=get_google_enum(val(v,'googleStatus')),picture_uploaded_date=None,suspended_date=None)
            if 'shadowLastChange' in v:
                user.shadow_last_change = val(v,'shadowLastChange')
            if 'shadowMax' in v:
                user.shadow_max = val(v,'shadowMax')
            user.save()
            email_address = clean_email(val(v,'mail'))
            if email_address:
                try:
                    email = EMails(address=email_address,content_object=user)
                    email.save()
                    # process email aliases also
                    if 'proxyaddress' in v:
                        for proxy in v['proxyaddress']:
                            if not isEmailAddressValid(proxy):
                                print "invalid email", proxy
                                continue
                            email_alias = EMailAliases(address=proxy,parent=email)
                            email_alias.save()
                except (ValidationError, IntegrityError), e:
                    print u, e
            elif 'proxyaddress' in v:
                print "user "+user.username+" doesn't have a primary email, but still has email aliases... not good!"

        print "Users done"

        # get groups from ldap
        ldap_groups = con.search_s(group_base_dn, ldap.SCOPE_SUBTREE, group_filter, group_attrs)

        print "Migrating groups", len(ldap_groups)
        ids = []
        empty = []
        def add_group(g):
            v = g[1]
            # skip ou=Luola (obsolete)
            if "ou=Luola" in g[0]:
                return
            # check the type of the group (project, server or generic group)
            if "ou=Projects" in g[0]:
                group = Projects(id=val(v,'gidNumber'),name=val(v,'cn'),description=val(v,'description') or "")
            elif "ou=Hosts" in g[0]:
                group = Servers(id=val(v,'gidNumber'),name=val(v,'cn'),description=val(v,'description') or "")
            else:
                group = Groups(id=val(v,'gidNumber'),name=val(v,'cn'),description=val(v,'description') or "")
                ids.append(group.id)
                if group.id is None:
                    empty.append(group)
            print g
            group.save()
            email_address = clean_email(val(v,'mail'))
            if email_address:
                email = EMails(address=email_address, content_object=group)
                try:
                    email.save()
                except (ValidationError, IntegrityError), e:
                    log.debug("DUPLICATE EMAIL; ADDING RANDOM PREFIX (these are not use yet --Vesa) ::cross fingers:: "+email_address)
                    email.address = email_address.replace('@','-tre@')
                    email.save()
                # email aliases
                if 'proxyaddress' in v:
                    for proxy in v['proxyaddress']:
                        if not isEmailAddressValid(proxy):
                            #print "invalid email", proxy
                            continue
                        mail_alias = EMailAliases(address=proxy, parent=email)
                        mail_alias.save()
            elif 'proxyaddress' in v:
                log.debug("group "+group.name+" doesn't have a primary email, but shill has email aliases... not good!")
            # group members
            if 'uniqueMember' in v:
                for member in v['uniqueMember']:
                    username = member[member.find('uid=')+4:member.find(',',member.find('uid='))]
                    try:
                        group.users.add(Users.objects.get(username=username))
                    except Users.DoesNotExist:
                        log.debug("user "+username+" doesn't exist in ldap anymore, group is "+group.name)
        teams = []
        for g in ldap_groups:
            # Teams have PK>3000, re-doing IDs (teamsmigrate does copies in LDAP)
            # - do these last, to not collide with other Groups
            if "ou=Teams" in g[0]:
                g[1]['gidNumber'] = None
                teams.append(g)
                continue
            add_group(g)
        for g in teams:
            try:
                add_group(g)
            except Exception, e:
                print e

        print "Groups done"

        # get sudoers from ldap
        ldap_sudoers = con.search_s(sudoer_base_dn, ldap.SCOPE_SUBTREE, sudoer_filter, sudoer_attrs)

        print "Migrating sudoers", len(ldap_sudoers)

        for s in ldap_sudoers:
            print s
            v = s[1]
            server_name = val(v,'cn')
            if server_name == 'defaults' or server_name == 'it-team':
                continue
            if 'sudoUser' in v:
                try:
                    server = Servers.objects.get(name=server_name)
                    for username in v['sudoUser']:
                        user = Users.objects.get(username=username)
                        server.sudoers.add(user)
                except Servers.DoesNotExist:
                    print "unknown server "+server_name
                except Users.DoesNotExist:
                    print "unknown user "+username

        print "Sudoers done"

        con.unbind()
        try:
            db.close()
        except Exception, e:
            print e

