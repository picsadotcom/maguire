from picsa_core.settings import *  # flake8: noqa

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'TESTSEKRET'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

# SECURITY WARNING: don't run with MD5PasswordHasher turned on in production!
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_ALWAYS_EAGER = True
BROKER_BACKEND = 'memory'
# CELERY_RESULT_BACKEND = 'djcelery.backends.database:DatabaseBackend'

AWS_S3_REGION_NAME = 'eu-central-1'
AWS_STORAGE_BUCKET_NAME = 'test-files'

POSTMARK_SERVER_TOKEN = 'POSTMARK_API_TEST'

EMAIL_DEVOPS = os.environ.get('EMAIL_DEVOPS', 'devops@example.com')

BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8000')
