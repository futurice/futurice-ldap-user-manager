from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from optparse import make_option
from datetime import datetime
import logging
import uuid

from fum.models import Users, Groups
from fum.common.util import random_ldap_password

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Disable users with suspend date > today.'
    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
            action='store_true',
            dest='dry',
            default=False,
            help='Print accouts that would be suspended. Do not suspend.'),
        make_option('--force',
            action='store_true',
            dest='force',
            default=False,
            help='Force run even if script has already ran today.'),
        )

    def handle(self, *args, **options):
        self.suspended = []
        self.activated = []
        dry = options['dry']
        force = options['force']
        if dry:
            log.info("Dry-run. Not really disabling.")

        now = timezone.now()
        for user in Users.objects.all():
            if user.suspended_date:
                if user.google_status == user.ACTIVEPERSON and (user.suspended_date - now).days <= 0:
                    log.info("Disabling user: %s %s (%s)"%(user.first_name, user.last_name, user.username))
                    self.suspended.append(user)
                    if dry:
                        continue

                    user.set_disabled()
                    user.suspended_date = None
                    user.save()
