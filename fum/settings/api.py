from prod import *

AUTHENTICATION_BACKENDS = DEFAULT_SETTINGS.AUTHENTICATION_BACKENDS
WSGI_APPLICATION = 'fum.wsgi.api.application'
ROOT_URLCONF = 'fum.api_urls'
