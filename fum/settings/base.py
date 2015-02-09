import django.conf.global_settings as DEFAULT_SETTINGS
import os, datetime, copy
import getpass
from pwd import getpwnam

PACKAGE_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
PROJECT_ROOT = os.path.normpath(PACKAGE_ROOT)
DEPLOYMENT_ROOT = PROJECT_ROOT
PROJECT_NAME = 'fum'

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'fum',
        'USER': '',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

OWNER = getpass.getuser()
OWNER_UID = getpwnam(OWNER).pw_uid
OWNER_GID = getpwnam(OWNER).pw_gid

EMAIL_PORT = 25
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

BADGE_URL = "https://fum.futurice.com/dbadge/create/"
VIMMA_URL = "https://vimma.futurice.com/vimma/vmm/create/"
API_URL = ""

# https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']
TIME_ZONE = 'Europe/Helsinki'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
USE_TZ = True

MEDIA_ROOT = '{PROJECT_ROOT}/media/'.format(**locals())
MEDIA_URL = '/media/'

# Location of users' portrait pictures
PORTRAIT_THUMB_FOLDER = '%sportraits/thumb/' % MEDIA_ROOT
PORTRAIT_THUMB_URL = '%sportraits/thumb/' % MEDIA_URL
PORTRAIT_FULL_FOLDER = '%sportraits/full/' % MEDIA_ROOT
PORTRAIT_FULL_URL = '%sportraits/full/' % MEDIA_URL

STATIC_ROOT = '{PROJECT_ROOT}/static/'.format(**locals())
STATIC_URL = '/static/'

MIDDLEWARE_CLASSES = (
    'fum.common.middleware.ThreadLocals',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'fum.urls'
WSGI_APPLICATION = 'fum.wsgi.local.application'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates/'),
)

TEMPLATE_CONTEXT_PROCESSORS  = (
    ('fum.common.context_processors.settings_to_context',
    'django.core.context_processors.request',
    )+DEFAULT_SETTINGS.TEMPLATE_CONTEXT_PROCESSORS)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    'django_extensions',
    'crispy_forms',
    #'haystack',
    'djangohistory',
    'rest_framework',
    'rest_framework_docs',
    'rest_framework.authtoken',
    'django_js_utils',

    'fum',
    'fum.common',
    'fum.users',
    'fum.groups',
    'fum.servers',
    'fum.projects',
    'fum.api',
)

AUTHENTICATION_BACKENDS = DEFAULT_SETTINGS.AUTHENTICATION_BACKENDS + (
    'django.contrib.auth.backends.RemoteUserBackend',
)

REST_FRAMEWORK = {
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.HyperlinkedModelSerializer',
    'DEFAULT_AUTHENTICATION_CLASSES': (     
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'PAGINATE_BY': 10,
    'PAGINATE_BY_PARAM': 'limit',
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.DjangoFilterBackend',
    ),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '[FUM] %(levelname)s %(asctime)s %(message)s'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'logfile': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/fum.log',
            'maxBytes': 50000,
            'backupCount': 2,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'fum':{
            'handlers': ['console', 'logfile'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_COOKIE_NAME = copy.deepcopy(PROJECT_NAME)
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'# TODO: json error in core.signing with JSONSerializer

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://127.0.0.1:8983/solr/',
        'TIMEOUT': 2,
    },
}
# TODO: use queue with celery
HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'
HAYSTACK_MAX_RESULTS = 25

# MIGRATION
ENFORCE_PROJECT_NAMING = True

# LDAP
import ldap
USE_TLS = True
LDAP_CLASS = 'fum.ldap_helpers.PoolLDAPBridge'
LDAP_RETRY_DELAY = 1
LDAP_RETRY_MAX = 3
LDAP_TIMEOUT = 5
LDAP_TRACE_LEVEL = 0
LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_TIMEOUT: LDAP_TIMEOUT,
    ldap.OPT_TIMELIMIT: LDAP_TIMEOUT,
    ldap.OPT_NETWORK_TIMEOUT: float(LDAP_TIMEOUT),
    ldap.OPT_PROTOCOL_VERSION: ldap.VERSION3,
}

# CHANGES WEBSOCKET ENDPOINT
CHANGES_SOCKET = '/tmp/fum3changes.sock'
CHANGES_SOCKET_ENABLED = True
CHANGES_FAILED_LOG = '/tmp/changes_failed.json'

SUDO_TIMEOUT = 90#in minutes
PROJECT_APPS = ['fum']

URLS_JS_GENERATED_FILE = 'fum/common/static/js/dutils.conf.urls.js'
URLS_JS_TO_EXPOSE = [
'api/',
'users/',
'groups/',
'servers/',
'projects/',
'search',
'superuser',
'audit',
]
URLS_EXCLUDE_PATTERN = ['.(?P<format>[a-z]+)', '\.(?P<format>[a-z0-9]+)']
URLS_BASE = '/fum/' # fum.futurice.com/fum/

FUM_LAUNCH_DAY = datetime.datetime.now().replace(year=2013, day=20, month=10)

CRISPY_TEMPLATE_PACK = 'bootstrap'

# According to https://github.com/futurice/futurice-ldap-user-manager/issues/33
# the minimum number of bits required to make a key secure depends on its type.
SSH_KEY_MIN_BITS_FOR_TYPE = {
    'ssh-ed25519': 256,
}
# For any key types not given above
SSH_KEY_MIN_BITS_DEFAULT = 2048

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

DJANGO_HISTORY_SETTINGS = {
'GET_CURRENT_REQUEST': ('fum.common.middleware', 'get_current_request'),
}
DJANGO_HISTORY_TRACK = False

try:
    # add any secrets here; local_settings needs to be somewhere in PYTHONPATH (eg. project-root, user-root)
    from local_settings import *
except Exception, e:
    print "No local_settings configured, ignoring..."
