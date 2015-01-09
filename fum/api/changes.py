"""
Signalling websocket endpoint about changes
"""
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.urlresolvers import NoReverseMatch

from fum.models import Users, Groups, Projects, Servers, AuditLogs
from fum.common.middleware import get_current_request
from fum.common.util import get_binary_fields

from rest_framework.reverse import reverse as rest_reverse
import urllib, json, datetime, socket, time, logging

from pprint import pprint as pp

log = logging.getLogger(__name__)

def dtnow():
    return datetime.datetime.now()

def changes_save(sender, instance, created, **kwargs):
    url, object_type = _get_url_and_type(instance)
    data = {
        'objectType': object_type,
        'objectUrl': url,
        'objectId': instance.name,
        'timestamp': dtnow(),
        'instance': instance,
        'attrs': [],
    }
    # on update, add attrs that changes
    action = 'update'
    if created:
        action = 'create'
    else:# list of all attributes that changed with old/new values
        attrs = []
        for k,v in instance.get_changes().iteritems():
            # do not log password changes
            if 'password' in k:
                continue
            # ignore binary information
            if any(binary_field_name in k for binary_field_name in get_binary_fields()):
                v['old'] = '(truncated)'
                v['new'] = '(truncated)'
            attrs.append({
                'attrName':k,
                'new':v['new'],
                'old':v['old']})
        data['attrs'] = attrs
    data['operation'] = action
    return send_data([data])

def changes_delete(sender, instance, **kwargs):
    url, object_type = _get_url_and_type(instance)
    data = {
        'operation': 'delete',
        'objectType': object_type,
        'objectUrl': url,
        'objectId': instance.name,
        'timestamp': dtnow(),
        'instance': instance,
        'attrs': [],
    }
    send_data([data])

def changes_update_m2m(instance, relation_name, old, new, action, related_instance):
    url, object_type = _get_url_and_type(instance)
    # Q: operation is always update, even when removing an entry?
    data = {
        'operation': 'update',
        'objectType': object_type,
        'objectUrl': url,
        'objectId': instance.name,
        'timestamp': dtnow(),
        'attrs': [],
        'instance': instance,
        'related_instance': related_instance,
    }
    data['attrs'].append({'attrName': relation_name, 'new': new, 'old': old})
    send_data([data])

def _get_url_and_type(instance):
    object_type = instance.__class__.__name__.lower().rstrip('s') # Server (instance) -> servers -> server
    return _get_url(instance), object_type

def _get_url(object_type, rdn_value=None): # API URL
    """
    <RegexURLPattern servers-detail ^servers/(?P<name>[^/]+)/$>,
    <RegexURLPattern servers-aliases ^servers/(?P<name>[^/]+)/aliases/$>,
    <RegexURLPattern servers-resources ^servers/(?P<name>[^/]+)/resources/$>,
    <RegexURLPattern servers-sudoers ^servers/(?P<name>[^/]+)/sudoers/$>,
    <RegexURLPattern servers-users ^servers/(?P<name>[^/]+)/users/$>,
    """
    try:
        return rest_reverse('%s-detail' % object_type.__class__.__name__.lower(), args=[getattr(object_type, 'name', object_type)])
    except NoReverseMatch, e:
        # TODO: Resource-model needs API entry
        print e
        return '/'

def send_data(data):
    """
    Send data to Changes-socket, making sure that if this fails, the data is saved
    and we retry next time we receive more data.
    """

    request = get_current_request()
    user = None
    if request and isinstance(request.user, User):
        user = request.user.get_fum_user()
    AuditLogs.objects.add(operation=data, user=user)

    # Verify format
    CHANGES_FORMAT_KEYS = ['operation','objectType','objectUrl','objectId','timestamp','attrs']
    final_data = []
    for k in data:
        tmp = {}
        for j in CHANGES_FORMAT_KEYS:
            tmp[j] = k[j]
        final_data.append(tmp)

    if not settings.CHANGES_SOCKET_ENABLED:
        log.debug('Changes websocket not enabled')
        return final_data

    # Load the data that we previously failed to send
    old_data = []
    try:
        with open(_failed_filepath, 'r') as fd:
            old_data = fd.read()
    except IOError:
        old_data = []
    else:
        if old_data:
            old_data = json.loads(old_data)
        else:
            old_data = []

    # Send old data and new data
    all_data = old_data + final_data
    json_data = json.dumps(all_data, default=_dthandler)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(settings.CHANGES_SOCKET)
        s.send(json_data)
    # If sending fails, adds the new data to previous failures
    except Exception as e:
        log.exception('Got exception on main handler')
        with open(_failed_filepath, 'w') as fd:
            fd.write(json.dumps(all_data, default=_dthandler))
    # If sending succeeds, empty the file
    else:
        with open(_failed_filepath, 'w') as fd:
            fd.write('')
    return final_data
_failed_filepath = settings.CHANGES_FAILED_LOG

def _dthandler(obj):
    if isinstance(obj, datetime.datetime):
        return time.mktime(obj.timetuple())

