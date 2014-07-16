from base import *
DEBUG = False
TEMPLATE_DEBUG = DEBUG
WSGI_APPLICATION = 'fum.wsgi.prod.application'

EMAIL_HOST = 'localhost'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

ADMINS = (
    ('Jussi Vaihia', 'jussi.vaihia@futurice.com'),
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'fum',
        'USER': 'fum',
        'PASSWORD': 'fum_xoxo',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

TEMPLATE_LOADERS = ('django.template.loaders.cached.Loader', DEFAULT_SETTINGS.TEMPLATE_LOADERS),

DEPLOYMENT_ROOT = os.path.normpath(os.path.join(PACKAGE_ROOT, '../..'))

OWNER = 'www-data'
MEDIA_ROOT = '{DEPLOYMENT_ROOT}/media/'.format(**locals())
# Location of users' portrait pictures
PORTRAIT_THUMB_FOLDER = '%sportraits/thumb/' % MEDIA_ROOT
PORTRAIT_FULL_FOLDER = '%sportraits/full/' % MEDIA_ROOT
from pwd import getpwnam
OWNER_UID = getpwnam(OWNER).pw_uid
OWNER_GID = getpwnam(OWNER).pw_gid

if LOGGING['handlers'].has_key('logfile'):
    del LOGGING['handlers']['logfile']
LOGGING['loggers']['fum']['handlers'] = ['console']

LDAP_RETRY_DELAY = 3
LDAP_RETRY_MAX = 7

API_URL = "https://api.fum.futurice.com"
URLS_BASE = '/fum/' # fum.futurice.com/fum/
