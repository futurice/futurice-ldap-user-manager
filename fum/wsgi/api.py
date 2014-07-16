import os
import site
from os.path import abspath, dirname, join

site.addsitedir('/srv/www/fum/venv/lib/python2.7/site-packages')
DJANGO_PROJECTDIR = abspath(join(dirname(__file__), '../..'))
ALLDIRS = [abspath(join(DJANGO_PROJECTDIR, '..')),]
site.addsitedir(abspath(join(DJANGO_PROJECTDIR, '')))
for directory in ALLDIRS:
    site.addsitedir(abspath(join(DJANGO_PROJECTDIR, directory)))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fum.settings.api")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
