from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from django.template.loader import get_template
from django.conf import settings
from django.template import Context

from optparse import make_option
from datetime import datetime
import logging
import uuid

from fum.models import Users, Groups
from fum.common.util import random_ldap_password
from django.core.mail import send_mail

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Disable users with suspend date > today and send reminder emails to users whose accounts are expiring in 1/7/14 day(s).'
    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
            action='store_true',
            dest='dry',
            default=False,
            help='Print accouts that would be suspended. Do not suspend or send reminder emails.'),
        make_option('--force',
            action='store_true',
            dest='force',
            default=False,
            help='Force run even if script has already ran today.'),
        )

    def handle(self, *args, **options):
        self.suspended = []
        self.activated = []
        self.emailed = []
        
        dry = options['dry']
        force = options['force']
        if dry:
            log.info("Dry-run. Not disabling or sending reminders.")

        now = timezone.now()
        remind_message = get_template('emails/suspend_reminder.txt')
        expired_message = get_template('emails/account_suspended.txt')

        for user in Users.objects.all():
            if user.suspended_date and user.google_status == user.ACTIVEPERSON:
                days_left = (user.suspended_date - now).days

                if days_left == 1 or days_left == 7 or days_left == 14:
                    log.info("Sending reminder email to %s %s (%s)"%(user.first_name, user.last_name, user.username))
                    subject = "Your %s account will expire in %d day%s."%(settings.COMPANY_NAME, days_left, "s" if days_left!=1 else "")
                    self.send(user, subject, remind_message, dry)

                elif days_left <= 0:
                    log.info("Disabling user: %s %s (%s)"%(user.first_name, user.last_name, user.username))
                    self.suspended.append(user)
                    subject = "%s password has expired."%(settings.COMPANY_NAME)
                    self.send(user, subject, expired_message, dry)

                    if dry:
                        continue

                    user.set_disabled()
                    user.suspended_date = None
                    user.save()

    def send(self, user, subject, body, dry):
        recipient_list = user.get_email()
        if recipient_list is not None:
            recipient_list = recipient_list.address
        if not recipient_list:
            return

        context = Context({ 'user': user })
        from_email = 'fum{0}'.format(settings.EMAIL_DOMAIN)
        message = body.render(context)

        self.emailed.append((user, {'message': message, 'subject': subject}))

        if not dry:
            send_mail(subject, message, from_email, [recipient_list], fail_silently=False)
