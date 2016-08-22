"""
Django settings for data_interrogator project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os,sys
BASE_DIR = os.path.dirname(__file__)
sys.path.insert(0, BASE_DIR)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'peralta_and_doyle'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'shop.apps.ShopConfig',
    'data_interrogator',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
)

ROOT_URLCONF = 'data_interrogator.tests.urls'

WSGI_APPLICATION = 'data_interrogator.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'tmp.db',
    }
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT=os.path.join(BASE_DIR, 'static')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
    },
]

TEMPLATE_DIRS = TEMPLATES[0]['DIRS']
USE_TZ = True

DATA_INTERROGATION_DOSSIER = {
    'suspects': [
        {   "model":("shop","Sale"),
            "wrap_sheets": {            },
            "aliases": { },
        },
        {'model':("shop","Product")},
        {'model':("shop","Branch")},
        {'model':("shop","SalesPerson")},
    ],
    'witness_protection' : ["User","Revision","Version"],
    'suspect_grouping':True
}
