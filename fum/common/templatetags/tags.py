from django import template
from django.conf import settings
from django.template.loader import render_to_string, get_template
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.contrib.sites.models import get_current_site
from django.shortcuts import get_object_or_404
from django.db.models.fields import FieldDoesNotExist

from datetime import datetime
from dateutil.relativedelta import relativedelta
from math import ceil
import json

from fum.common.assets import assets as assetgen
from fum.common.util import pretty_diff
from fum.models import Users, Groups

register = template.Library()
    
@register.simple_tag() # used outside of templates
def assets(path):
    return assetgen(path)

@register.assignment_tag(takes_context=True)
def superuser(context):
    request = context['request']
    user = get_object_or_404(Users, username=request.user.username)
    try:
        group = Groups.objects.get(name=settings.IT_TEAM)
    except Groups.DoesNotExist, e:
        group = None
    return group and user.in_group(group)

@register.assignment_tag(takes_context=True)
def sudomode(context):
    request = context['request']
    timeout = request.session.get('sudo_timeout', None)
    if timeout is None or timeout < datetime.utcnow():
        if timeout is not None:
                request.session.pop('sudo_timeout')
        return False
    return True

@register.assignment_tag(takes_context=True)
def editable(context, instance, field):
    if field not in instance.restricted_fields:
        return True

    request = context['request']
    user = get_object_or_404(Users, username=request.user.username)

    try: 
        group = instance.editor_group
    except:
        group = None

    if user.is_sudo_user(request):
        return True
    elif field == 'password' and instance==user:
        return True
    elif group:
        if not user.in_group(group):
            return False
    
    return False

@register.simple_tag()
def sudo_time_left(sudo_ends):
    time_left = (sudo_ends-datetime.utcnow()).seconds
    if time_left <= 60:
        return time_left
    else:
        return int(ceil(time_left/60.0))

# Hack to avoid timezone problems
@register.simple_tag()
def sudo_time_expires_timestamp(sudo_ends):
    diff = (datetime.now()-datetime.utcnow())
    return (sudo_ends+diff).strftime("%s")

@register.simple_tag()
def lookup(object, property):
    try:
        choices = object._meta.get_field_by_name(property)[0].choices
    except FieldDoesNotExist, e:
        choices = None
    if choices:
        result = getattr(object, 'get_%s_display'%property)()
    else:
        if callable(getattr(object, property)): # get_email()
            result =  getattr(object, property)()
        else:
            result = getattr(object, property, None)
    if result is None: result = ''
    return result

@register.simple_tag()
def prettydiff(a, b):
    return pretty_diff(a, b)

@register.filter(is_safe=True)
def xeditable_value(value):
    if value is None:
        return ''
    return json.dumps(int(value))

@register.simple_tag()
def warncolor(dt, red=0, yellow=30):
    """ Green, Yellow, Red -warning color based on hours remaining relative to current time """
    daymonthyear = lambda x: datetime(*(x[:3]))
    now = daymonthyear(datetime.today().timetuple())
    dt = daymonthyear(dt.timetuple())
    if ( now >= dt-relativedelta(hours=red) ):
        return 'red'
    elif ( now >= dt-relativedelta(hours=yellow) ):
        return 'yellow'
    else:
        return 'green'
