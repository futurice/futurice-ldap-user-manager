import re
from fum.models import PROJECT_NAME_REGEX
from django.conf import settings

def name_to_email(name):
    strings = re.findall(PROJECT_NAME_REGEX, name)
    if not strings:
        raise ValueError('Invalid project name', name)
    parts = [k.lower() for k in strings[0]]
    parts.append(settings.EMAIL_DOMAIN)
    email = 'project-{0}-{1}{2}'.format(*parts)
    return email
