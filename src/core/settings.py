"""generalised settings for the Lax project.

per-instance settings are in /path/to/app/app.cfg
example settings can be found in /path/to/lax/elife.cfg

./install.sh will create a symlink from dev.cfg -> lax.cfg if lax.cfg not found."""

import os
from os.path import join
from datetime import datetime
import ConfigParser as configparser
from pythonjsonlogger import jsonlogger
import yaml
from et3.render import render_item
from et3.extract import path as p

PROJECT_NAME = 'lax'

# Build paths inside the project like this: os.path.join(SRC_DIR, ...)
SRC_DIR = os.path.dirname(os.path.dirname(__file__)) # ll: /path/to/lax/src/
PROJECT_DIR = os.path.dirname(SRC_DIR) # ll: /path/to/lax/

CFG_NAME = 'app.cfg'
DYNCONFIG = configparser.SafeConfigParser(**{
    'allow_no_value': True,
    'defaults': {'dir': SRC_DIR, 'project': PROJECT_NAME}})
DYNCONFIG.read(join(PROJECT_DIR, CFG_NAME)) # ll: /path/to/lax/app.cfg

def cfg(path, default=0xDEADBEEF):
    try:
        return DYNCONFIG.get(*path.split('.'))
    except (configparser.NoOptionError, configparser.NoSectionError): # given key in section hasn't been defined
        if default == 0xDEADBEEF:
            raise ValueError("no value/section set for setting at %r" % path)
        return default

PRIMARY_JOURNAL = {
    'name': cfg('journal.name'),
    'inception': datetime.strptime(cfg('journal.inception'), "%Y-%m-%d")
}

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = cfg('general.secret-key')

DEBUG = cfg('general.debug')

DEV, TEST, PROD = 'dev', 'test', 'prod'
ENV = cfg('general.env', DEV)

ALLOWED_HOSTS = cfg('general.allowed-hosts', '').split(',')

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_swagger',
    'django_markdown2',

    'explorer',

    'publisher',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(SRC_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': cfg('general.debug'),
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Testing
TEST_RUNNER = 'xmlrunner.extra.djangotestrunner.XMLTestRunner'
TEST_OUTPUT_DIR = 'build'
TEST_OUTPUT_FILE_NAME = 'junit.xml'

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': cfg('database.engine'),
        'NAME': cfg('database.name'),
        'USER': cfg('database.user'),
        'PASSWORD': cfg('database.password'),
        'HOST': cfg('database.host'),
        'PORT': cfg('database.port')
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

MEDIA_ROOT = os.path.join(SRC_DIR, 'media')
STATIC_ROOT = os.path.join(PROJECT_DIR, 'collected-static')

STATICFILES_DIRS = (
    os.path.join(SRC_DIR, "static"),
)

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    #'DEFAULT_PERMISSION_CLASSES': [
    #    'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    #],
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [],
    #'DEFAULT_CONTENT_NEGOTIATION_CLASS': 'publisher.negotiation.eLifeContentNegotiation',
    'DEFAULT_RENDERER_CLASSES': (
        'publisher.negotiation.ArticleListVersion1',
        'publisher.negotiation.POAArticleVersion1',
        'publisher.negotiation.VORArticleVersion1',
        'publisher.negotiation.ArticleHistoryVersion1',
        'rest_framework.renderers.JSONRenderer',
        #'rest_framework.renderers.BrowsableAPIRenderer',
    )
}

SWAGGER_SETTINGS = {
    'api_version': '1',
    'exclude_namespaces': ['proxied'], # swagger docs are broken, but this gives them the right namespace
}

#
# API opts
#

SCHEMA_PATH = join(PROJECT_DIR, 'schema/api-raml/dist')
SCHEMA_IDX = {
    'poa': join(SCHEMA_PATH, 'model/article-poa.v1.json'),
    'vor': join(SCHEMA_PATH, 'model/article-vor.v1.json'),
    'history': join(SCHEMA_PATH, 'model/article-history.v1.json'),
    'list': join(SCHEMA_PATH, 'model/article-list.v1.json')
}
API_PATH = join(SCHEMA_PATH, 'api.raml')

def _load_api_raml(path):
    yaml.add_multi_constructor('', lambda *args: '[disabled]')
    return yaml.load(open(path, 'r'))['traits']['paged']['queryParameters']

API_OPTS = render_item({
    'per_page': [p('per-page.default'), int],
    'min_per_page': [p('per-page.minimum'), int],
    'max_per_page': [p('per-page.maximum'), int],

    'page_num': [p('page.default'), int],

    'order_direction': [p('order.default')],

}, _load_api_raml(API_PATH))

#
# notification events
#

EVENT_BUS = {
    'region': cfg('bus.region'),
    'subscriber': cfg('bus.subscriber'),
    'name': cfg('bus.name'),
    'env': cfg('bus.env')
}

# ll: arn:aws:sns:us-east-1:112634557572:bus-articles--ci
TOPIC_ARN = "arn:aws:sns:{region}:{subscriber}:{name}--{env}".format(**EVENT_BUS)

# Lax settings

# when ingesting an article version and the EIF has no 'update' value,
# should we fail and raise an error? if not, the article pub-date is used instead.
FAIL_ON_NO_UPDATE_DATE = cfg('ingest.fail-on-no-update-date', False)

LOG_NAME = '%s.log' % PROJECT_NAME # ll: lax.log
LOG_FILE = join(PROJECT_DIR, LOG_NAME) # ll: /path/to/lax/log/lax.log

INGESTION_LOG_NAME = 'ingestion-%s.log' % PROJECT_NAME
INGESTION_LOG_FILE = join(PROJECT_DIR, INGESTION_LOG_NAME)

if ENV != DEV:
    LOG_FILE = join('/var/log/', LOG_NAME) # ll: /var/log/lax.log
    INGESTION_LOG_FILE = join('/var/log/', INGESTION_LOG_NAME) # ll: /var/log/lax.log

# whereever our log files are, ensure they are writable before we do anything else.
def writable(path):
    os.system('touch ' + path)
    # https://docs.python.org/2/library/os.html
    assert os.access(path, os.W_OK), "file doesn't exist or isn't writable: %s" % path
map(writable, [LOG_FILE, INGESTION_LOG_FILE])

ATTRS = ['asctime', 'created', 'levelname', 'message', 'filename', 'funcName', 'lineno', 'module', 'pathname']
FORMAT_STR = ' '.join(map(lambda v: '%(' + v + ')s', ATTRS))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'json': {
            '()': jsonlogger.JsonFormatter,
            'format': FORMAT_STR,
        },
        'brief': {
            'format': '%(levelname)s - %(message)s'
        },
    },

    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': LOG_FILE,
            'formatter': 'json',
        },
        'ingestion': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': INGESTION_LOG_FILE,
            'formatter': 'json',
        },
        'debug-console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'brief',
        },
    },

    'loggers': {
        '': {
            'handlers': ['debug-console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'publisher.eif_ingestor': {
            'handlers': ['ingestion'],
        },
        'publisher.ejp_ingestor': {
            'handlers': ['ingestion'],
        },
        'publisher.ajson_ingestor': {
            'handlers': ['ingestion'],
            #'propagate': False, # prevent propagation to root handler and it's debug-console handler
        },
        'publisher.management.commands.import': {
            'level': 'INFO',
            'handlers': ['debug-console'],
        },
        'publisher.management.commands.ingest': {
            'level': 'INFO',
            'handlers': ['ingestion', 'debug-console'],
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
