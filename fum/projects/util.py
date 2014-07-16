import re
from fum.models import PROJECT_NAME_REGEX

def name_to_email(name):
    parts = [k.lower() for k in re.findall(PROJECT_NAME_REGEX, name)[0]]
    email = 'project-{0}-{1}@futurice.com'.format(*parts)
    return email
