from base import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'django',
        'USER': 'postgres',
        'PASSWORD': 'localtest',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}