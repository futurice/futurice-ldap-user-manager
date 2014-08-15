from django.conf import settings
from django.core.mail import send_mail as django_send_mail
from django.core.serializers.json import DjangoJSONEncoder
import string, random, json
import diff_match_patch

generator = random.SystemRandom()

class LazyDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError("'%s' object has no attribute '%s'" % (self.__class__.__name__, key))
    def __setattr__(self, attr, value):
        self[attr] = value

def id_generator(size=10, chars=string.printable):
    return ''.join(generator.choice(chars) for x in range(size))

def to_json(data):
    return json.dumps(data, encoding='utf-8', cls=DjangoJSONEncoder, ensure_ascii=False, separators=(',',':'))

def pretty_diff(a, b):
    d = diff_match_patch.diff_match_patch()
    e = d.diff_main(a, b)
    return d.diff_prettyHtml(e)

def ldap_log(data):
    try:
        tmp = []
        for k,v in enumerate(data):
            v = list(v)
            # ignore binary information
            if any(binary_field_name in v for binary_field_name in get_binary_fields()):
                v[2] = '(truncated)'
            tmp.append(v)
        return to_json(tmp)
    except Exception,e:
        return '(ldap_log failed: %s)'%e

def get_binary_fields():
    return ['jpeg_portrait','jpegPhoto']

def send_mail(subject, message, from_email, recipient_list, fail_silently=False):
    return django_send_mail(subject=subject, message=message, from_email=from_email, recipient_list=recipient_list, fail_silently=fail_silently)

def random_ldap_password(size=10, types=None):
    """ An LDAP password is a combination of lowercase, uppercase, digits, and special characters with characters from atleast three groups present """
    types = types or [string.lowercase, string.uppercase, '123456789', '#./+-_&"%']
    bucket_size = size/len(types)
    buckets = len(types)*[bucket_size]
    buckets[0] += size-sum(buckets)
    seq = [ id_generator(size=buckets[k], chars=chars) for k,chars in enumerate(types) ]
    random.shuffle(seq)
    return ''.join(seq)

def create_mandatory_groups():
    from fum.models import Groups
    for group in settings.PROTECTED_GROUPS:
        Groups.objects.get_or_create(name=group)

import requests
class SMS(object):
    def send(self, to, message):
        params = {'to': to,
                'text': message,
                'username': settings.SMS_USER,
                'password': settings.SMS_PASSWORD,
                }
        response = LazyDict(dict(status_code=200, content='0: Delivered (DEBUG)', message=message, to=to))
        if not settings.DEBUG:
            response = requests.get(settings.SMS_URL, params=params, verify=False)
        return response
