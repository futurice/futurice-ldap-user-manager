from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.template.loader import get_template
from django.template import Context
from django.forms import EmailField
from django.core.exceptions import ValidationError
from django.utils.encoding import smart_unicode

import re
from optparse import make_option
import logging, time

from fum.models import *

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Copy a group to a new group'
    option_list = BaseCommand.option_list + (
        make_option('--from',
            action='store',
            dest='from_group',
            help='From Grop'),
        make_option('--to',
            action='store',
            dest='to_group',
            help='To Group'),
        )
    def handle(self, *args, **options):
        fg = Groups.objects.get(name=options.get('from_group'))
        tg,_ = Groups.objects.get_or_create(name=options.get('to_group'))
        print "Copying users from {0} to {1}".format(fg, tg)
        for k in fg.users.all():
            tg.users.add(k)
            time.sleep(0.1)
