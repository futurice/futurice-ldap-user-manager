from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.template.loader import get_template
from django.template import Context
from django.conf import settings
from django.utils.timezone import now

from datetime import datetime
from optparse import make_option
import logging
import os

from fum.models import Users
from fum.common.util import random_ldap_password

from django.core.mail import send_mail

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Checks for passwords that are about to expire and sends reminders for those users. Use password and/or remind as arguments.'
    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
            action='store_true',
            dest='dry',
            default=False,
            help='Do not send emails, print out would-be recipients.'),
        make_option('--force',
            action='store_true',
            dest='force',
            default=False,
            help='Force run even if script has already ran today.'),
        )

    def handle(self, *args, **options):
        self.emailed = []
        dry = options['dry']
        force = options['force']
        command = ''

        if dry:
            log.info("Dry-run. I'm not really sending any emails.")
        dtnow = now()

        if 'password' in args:
            log.info("Reminding users of expiring passwords.")
            command = 'password'

        if 'password' not in args and 'suspend' not in args:
            log.info('Use "password" and/or "suspend" as keywords to specify what to remind of. e.g. ... remind password')
            return 

        LOG_DIR = u'%s/logs/'%settings.DEPLOYMENT_ROOT
        LOG_FILE = u'%sremind_lastrun_%s'%(LOG_DIR, command)
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)

        try:
            with open(LOG_FILE, 'r') as f:
                text = f.read()
            filedate = datetime.strptime(text, "%Y-%m-%d").date()
            if not force and dtnow.date() == filedate:
                log.info('Reminders have already been sent today. Use --force to send again.')
                return
        except ValueError:
            log.info('No "lastrun" file with valid datetime found. Assuming first run.')
        except IOError:
            log.info('No "lastrun" file found. Assuming first run.')


        log.info("Started...")
        for user in Users.objects.all():
            if user.google_status == user.ACTIVEPERSON:
                if 'password' in args:
                    body = get_template('emails/password_reminder.txt')
                    days_left = (user.password_expires_date - dtnow).days
                    subject = "%s password will expire in %d day%s."%(settings.COMPANY_NAME, days_left, "s" if days_left!=1 else "")
                    if days_left < 0:
                        log.info("password expired: %s"%(user))
                        user.set_ldap_password(random_ldap_password())
                        self.send(user, "%s password has expired."%(settings.COMPANY_NAME), get_template('emails/password_expired.txt'), dry)
                    elif days_left <= 7:
                        self.send(user, subject, body, dry)
                    elif days_left == 14:
                        self.send(user, subject, body, dry)
                    elif days_left == 30:
                        self.send(user, subject, body, dry)

        with open(LOG_FILE, 'w') as f:
            text = dtnow.date().strftime("%Y-%m-%d")
            f.write(text)
        os.chmod(LOG_FILE, 0777)

        log.info("Done!")

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
