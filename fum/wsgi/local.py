import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fum.settings.base")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
