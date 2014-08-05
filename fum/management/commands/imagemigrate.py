from optparse import make_option
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from fum.models import Users
import ldap
import os
import logging
from datetime import datetime

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Image migration'
    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
            action='store_true',
            dest='dry',
            default=False,
            help='Image migration'),
        )

    def handle(self, *args, **options):
        print "Disabling changes-socket"
        setattr(settings, 'CHANGES_SOCKET_ENABLED', False)
        print "Disabling LDAP sync"
        setattr(settings, 'LDAP_CLASS', 'fum.ldap_helpers.DummyLdap')
        print "Disabling Solr sync"
        setattr(settings, 'HAYSTACK_SIGNAL_PROCESSOR', 'haystack.signals.BaseSignalProcessor')

        log.info("Running")
        # LDAP connection
        ldap_server = settings.MIGRATION['LDAP']['uri']
        dn = settings.MIGRATION['LDAP']['bind_dn']
        pw = settings.MIGRATION['LDAP']['bind_pwd']

        # Ignore certificates
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, 0)

        # open connections
        con = ldap.initialize(ldap_server)
        con.start_tls_s()
        con.simple_bind_s(dn,pw)

        # LDAP user's images
        user_base_dn = settings.USER_DN
        user_filter = "(objectclass=person)"
        user_attrs = ['uid','jpegPhoto']

        # path to save images
        thumb_path = settings.PORTRAIT_THUMB_FOLDER

        # get users from ldap
        ldap_users = con.search_s(user_base_dn, ldap.SCOPE_SUBTREE, user_filter, user_attrs)

        # create directory for portraits, if not existing
        if not os.path.exists(settings.PORTRAIT_FULL_FOLDER):
            os.makedirs(settings.PORTRAIT_FULL_FOLDER)
        if not os.path.exists(thumb_path):
            os.makedirs(thumb_path)

        n = datetime.now()

        # munch away!
        for u in ldap_users:
            if 'jpegPhoto' in u[1]:
                user = Users.objects.get(username = u[1]['uid'][0])
                image_name = "%s%s.jpeg" % (u[1]['uid'][0], n.strftime('%Y%m%d%H%M%S'))
                user.portrait_thumb_name = image_name
                user.save()
                f = open("%s%s" % (thumb_path, image_name), 'wb')
                f.write(u[1]['jpegPhoto'][0])
                f.close()

        # set ownership of files, as outside of WSGI
        os.system('chown -R %s %s'%(settings.OWNER, settings.PORTRAIT_FULL_FOLDER))
        os.system('chown -R %s %s'%(settings.OWNER, thumb_path))

        con.unbind()
