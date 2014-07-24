import re
from fum.models import PROJECT_NAME_REGEX

def name_to_email(name):
    strings = re.findall(PROJECT_NAME_REGEX, name)
    if not strings:
        raise ValueError('Invalid project name', name)
    parts = [k.lower() for k in strings[0]]
    email = 'project-{0}-{1}@futurice.com'.format(*parts)
    return email
