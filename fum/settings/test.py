import django.conf.global_settings as DEFAULT_SETTINGS
import sys
from base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'fumdb',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.BaseSignalProcessor'
CHANGES_SOCKET_ENABLED = False
LDAP_MOCK = True
LDAP_CLASS = 'fum.ldap_helpers.LDAPBridge'

if sys.argv and 'test' in sys.argv:
    print "TEST_MODE: Disabling RemoteUserMiddleware"
    # NOTE: Disabling RemoteUserMiddleware. In Django 1.6+ the frameworks own tests are not run, and this will be unnecessary.
    test_breaking_cls = 'django.contrib.auth.middleware.RemoteUserMiddleware'
    if test_breaking_cls in MIDDLEWARE_CLASSES:
        MIDDLEWARE_CLASSES = [k for k in MIDDLEWARE_CLASSES if k not in [test_breaking_cls]]
        AUTHENTICATION_BACKENDS = DEFAULT_SETTINGS.AUTHENTICATION_BACKENDS
