"""
Django settings for maguire project.

Generated by 'django-admin startproject' using Django 1.11.6.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import json

import dj_database_url
from kombu import Exchange, Queue

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', "REPLACEME")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', False)

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    # admin
    'django.contrib.admin',
    # core
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 3rd party
    'raven.contrib.django.raven_compat',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_auth',
    'django_filters',
    'corsheaders',
    'reversion',
    'graphene_django',
    'rolepermissions',
    'django_celery_beat',
    'opbeat.contrib.django',
    # us
    'credits',
    'debits',
    'events',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'reversion.middleware.RevisionMiddleware',
    'opbeat.contrib.django.middleware.OpbeatAPMMiddleware',
]

ROOT_URLCONF = 'maguire.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'maguire.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get(
            'MAGUIRE_DATABASE',
            'postgres://:@/maguire')),
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',  # noqa
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',  # noqa
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',  # noqa
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',  # noqa
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

MEDIA_URL = '/media/'
STATIC_ROOT = 'staticfiles'
STATIC_URL = '/static/'

# Sentry configuration
RAVEN_CONFIG = {
    # DevOps will supply you with this.
    'dsn': os.environ.get('MAGUIRE_SENTRY_DSN', None),
}

# CORS Support
CORS_ORIGIN_ALLOW_ALL = True

# REST Framework conf defaults
REST_FRAMEWORK = {
    'PAGE_SIZE': 100,
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',)  # noqa
}

# GRAPHENE = {
#     'SCHEMA': 'maguire.schema.schema',
#     'MIDDLEWARE': (
#         'graphene_django.debug.DjangoDebugMiddleware',
#     )
# }

# Celery configuration options

CELERY_BROKER_URL = os.environ.get('MAGUIRE_BROKER_URL',
                                   'amqp://guest:guest@localhost:5672//')

CELERY_DEFAULT_QUEUE = 'maguire'
CELERY_QUEUES = (
    Queue('maguire',
          Exchange('maguire'),
          routing_key='maguire'),
)

CELERY_ALWAYS_EAGER = False

# Tell Celery where to find the tasks
CELERY_IMPORTS = (
    'debits.tasks',
    'events.tasks',
)

CELERY_CREATE_MISSING_QUEUES = True
CELERY_ROUTES = {
    'celery.backend_cleanup': {
        'queue': 'mediumpriority',
    },
    'maguire.debits.tasks.t_queue_pending': {
        'queue': 'maguire',
    },
}

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

ROLEPERMISSIONS_MODULE = 'maguire.roles'

EMAIL_BACKEND = 'postmarker.django.EmailBackend'
EMAIL_DEVOPS = os.environ.get('EMAIL_DEVOPS', 'REPLACEME')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'REPLACEME@example.org')  # noqa
POSTMARK = {
    'TOKEN': os.environ.get('POSTMARK_SERVER_TOKEN', 'REPLACEME'),
    'TEST_MODE': False,
    'VERBOSITY': 0,
}
POSTMARK_SERVER_TOKEN = os.environ.get('POSTMARK_SERVER_TOKEN', 'REPLACEME')

AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'REPLACEME')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'REPLACEME')
AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'REPLACEME')
AWS_S3_AIRFLOW_BUCKET = os.environ.get('AWS_S3_AIRFLOW_BUCKET', 'REPLACEME')
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'REPLACEME')  # noqa
AWS_DEFAULT_ACL = 'private'
AWS_S3_ENCRYPTION = True

BASE_URL = os.environ.get('BASE_URL', 'REPLACEME')

OPBEAT = {
    'ORGANIZATION_ID': os.environ.get('OPBEAT_ORGANIZATION_ID', 'REPLACEME'),
    'APP_ID': os.environ.get('OPBEAT_APP_ID', 'REPLACEME'),
    'SECRET_TOKEN': os.environ.get('OPBEAT_SECRET_TOKEN', 'REPLACEME'),
}

# These tokens are used when hitting callback URLs to secure them
CALLBACK_TOKEN_DEBITS = os.environ.get('CALLBACK_TOKEN_DEBIT', None)
CALLBACK_TOKEN_CREDITS = os.environ.get('CALLBACK_TOKEN_CREDITS', None)

DEBIT_PROVIDER = os.environ.get('DEBIT_PROVIDER', 'debits.providers.easydebit')
DEBIT_PACKAGE = os.environ.get('DEBIT_PACKAGE', 'EasyDebitProvider')
DEBIT_CONFIG = json.loads(os.environ.get('DEBIT_CONFIG', '{}'))
