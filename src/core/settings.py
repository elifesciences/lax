"""generalised settings for the Lax project.

per-instance settings are in /path/to/lax/app.cfg
example settings can be found in /path/to/lax/elife.cfg

`./install.sh` creates a symlink from `elife.cfg` to `app.cfg` if `app.cfg` not found."""

import os
import multiprocessing
from os.path import join
from datetime import datetime
import configparser as configparser
from pythonjsonlogger import jsonlogger
import json, yaml
from et3.render import render_item
from et3.extract import path as p

PROJECT_NAME = "lax"

# Build paths inside the project like this: os.path.join(SRC_DIR, ...)
SRC_DIR = os.path.dirname(os.path.dirname(__file__))  # "/path/to/lax/src/"
PROJECT_DIR = os.path.dirname(SRC_DIR)  # "/path/to/lax/"

CFG_NAME = "app.cfg"
DYNCONFIG = configparser.ConfigParser(
    **{"allow_no_value": True, "defaults": {"dir": SRC_DIR, "project": PROJECT_NAME}}
)
DYNCONFIG.read(join(PROJECT_DIR, CFG_NAME))  # "/path/to/lax/app.cfg"


def cfg(path, default=0xDEADBEEF):
    lu = {
        "True": True,
        "true": True,
        "False": False,
        "false": False,
    }  # cast any obvious booleans
    try:
        val = DYNCONFIG.get(*path.split("."))
        return lu.get(val, val)
    # given key in section hasn't been defined
    except (
        configparser.NoOptionError,
        configparser.NoSectionError,
    ):
        if default == 0xDEADBEEF:
            raise ValueError("no value/section set for setting at %r" % path)
        return default
    except Exception as err:
        print("error on %r: %s" % (path, err))


PRIMARY_JOURNAL = {
    "name": cfg("journal.name"),
    "inception": datetime.strptime(cfg("journal.inception"), "%Y-%m-%d"),
}

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = cfg("general.secret-key")

DEBUG = cfg("general.debug")
assert isinstance(
    DEBUG, bool
), "'debug' must be either True or False as a boolean, not %r" % (DEBUG,)

ALLOWED_HOSTS = cfg("general.allowed-hosts", "").split(",")

# Application definition

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_markdown2",  # landing page is rendered markdown
    "explorer",  # sql creation
    # 'django_db_logger', # logs certain entries to the database
    "publisher",
)

# order is tricky here.
# the request descends this list and responses ascend.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # content types are deprecated before being removed entirely
    "publisher.middleware.mark_deprecated",
    "core.middleware.KongAuthentication",  # sets a header if it looks like an authenticated request
    "publisher.middleware.error_content_check",
    # order is important here.
    "publisher.middleware.content_check",
    "publisher.middleware.downgrade_poa_content_type",
    "publisher.middleware.downgrade_vor_content_type",
    "core.middleware.DownstreamCaching",
]

ROOT_URLCONF = "core.urls"

# https://docs.djangoproject.com/en/1.10/ref/middleware/#module-django.middleware.common
# USE_ETAGS = True # lsh@2020-09: deprecated in Django 2.1, not sure we actually use it

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(SRC_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": cfg("general.debug"),
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "core.wsgi.application"

# a process-wide manager is only available if lax is called with LAX_MULTIPROCESSING=1
# this manager is not available from uwsgi-started process or a fork
MP_MANAGER = (
    multiprocessing.Manager() if os.environ.get("LAX_MULTIPROCESSING") else None
)

# Testing
# lsh@2019-08-05: pytest doesn't use this but the output path is the same
TEST_RUNNER = "xmlrunner.extra.djangotestrunner.XMLTestRunner"
TEST_OUTPUT_DIR = "build"
TEST_OUTPUT_FILE_NAME = "junit.xml"

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

# CONN_MAX_AGE = 60 # seconds.
# 2020-12-18: 'idle_in_transaction_session_timeout' for PSQL 11.1+ under RDS is 12 hours.
# this should be less than that.
# CONN_MAX_AGE = 0 # default
CONN_MAX_AGE = 120  # seconds, arbitrary.

DATABASES = {
    "default": {
        "ENGINE": cfg("database.engine"),
        "NAME": cfg("database.name"),
        "USER": cfg("database.user"),
        "PASSWORD": cfg("database.password"),
        "HOST": cfg("database.host"),
        "PORT": cfg("database.port"),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

STATIC_URL = "/static/"
MEDIA_URL = "/media/"

MEDIA_ROOT = join(SRC_DIR, "media")
STATIC_ROOT = join(PROJECT_DIR, "collected-static")

STATICFILES_DIRS = (os.path.join(SRC_DIR, "static"),)

#
# sql explorer
#

EXPLORER_S3_BUCKET = cfg("general.reporting-bucket", None)
EXPLORER_CONNECTIONS = {"default": "default"}
EXPLORER_DEFAULT_CONNECTION = "default"

#
# API opts
#

CONTENT_TYPES = "poa", "vor", "history", "list", "related"
POA, VOR, HISTORY, LIST, RELATED = CONTENT_TYPES

SCHEMA_PATH = join(PROJECT_DIR, "schema", "api-raml", "dist")

# a response is valid if it validates under any version of it's schema.
# order is important. if all attempts to validate fail, the first validation error is re-raised
ALL_SCHEMA_IDX = {
    POA: [
        (3, join(SCHEMA_PATH, "model/article-poa.v3.json")),
        (2, join(SCHEMA_PATH, "model/article-poa.v2.json")),
    ],
    VOR: [
        (6, join(SCHEMA_PATH, "model/article-vor.v6.json")),
        (5, join(SCHEMA_PATH, "model/article-vor.v5.json")),
    ],
    HISTORY: [
        (2, join(SCHEMA_PATH, "model/article-history.v2.json")),
        (1, join(SCHEMA_PATH, "model/article-history.v1.json")),
    ],
    LIST: [(1, join(SCHEMA_PATH, "model/article-list.v1.json"))],
    RELATED: [(1, join(SCHEMA_PATH, "model/article-related.v1.json"))],
}

# {"vor": "/path/to/model/article-vor.v5.json", "poa": ...}
SCHEMA_IDX = {tpe: rows[0][1] for tpe, rows in ALL_SCHEMA_IDX.items()}

# {"vor": [5, 4], "history": [2, 1], ...}
SCHEMA_VERSIONS = {
    tpe: [row[0] for row in rows] for tpe, rows in ALL_SCHEMA_IDX.items()
}

# {"/path/to/model/article-vor.v5.json": {...}, ...}
SCHEMA_MAP = {}
for path_list in ALL_SCHEMA_IDX.values():
    for _, path in path_list:
        SCHEMA_MAP[path] = json.load(open(path, "rb"))

API_PATH = join(SCHEMA_PATH, "api.raml")

# a schema failure may have multiple independent failures and each failure
# may have multiple possibilities.
NUM_SCHEMA_ERRORS = NUM_SCHEMA_ERROR_SUBS = 10


def _load_api_raml(path):
    # load the api.raml file, ignoring any "!include" commands
    yaml.add_multi_constructor("", lambda *args: "[disabled]")
    api = yaml.load(open(path, "r"), Loader=yaml.FullLoader)
    return api["traits"]["paged"]["queryParameters"]


API_OPTS = render_item(
    {
        "per_page": [p("per-page.default"), int],
        "min_per_page": [p("per-page.minimum"), int],
        "max_per_page": [p("per-page.maximum"), int],
        "page_num": [p("page.default"), int],
        "order_direction": [p("order.default")],
    },
    _load_api_raml(API_PATH),
)

# load raw SQL

SQL_PATH = join(PROJECT_DIR, "schema", "sql")
SQL_LIST = [
    "internal-relationships-for-msid.sql",
    "internal-reverse-relationships-for-msid.sql",
    "external-relationships-for-msid.sql"
]
SQL_MAP = {os.path.basename(path): open(os.path.join(SQL_PATH, path), "r").read()
           for path in SQL_LIST}

# KONG gateway options

KONG_AUTH_HEADER = "KONG-Authenticated"
INTERNAL_NETWORKS = ["10.0.0.0/16", "127.0.0.0/8"]

#
# notification events
#

EVENT_BUS = {
    "region": cfg("bus.region"),
    "subscriber": cfg("bus.subscriber"),
    "name": cfg("bus.name"),
    "env": cfg("bus.env"),
}

# Lax settings

# toggle to bypass the creation of relationships between articles internally
ENABLE_RELATIONS = True
# when ingesting an article, if an article says it's related to an article that doesn't exist, should an Article stub be created? default, True.
RELATED_ARTICLE_STUBS = cfg("general.related-article-stubs", True)

# allow fragments pushed in from other sources?
MERGE_FOREIGN_FRAGMENTS = cfg("general.merge-foreign-fragments", True)

#
# logging
#

LOG_NAME = "%s.log" % PROJECT_NAME  # "lax.log"

INGESTION_LOG_NAME = "ingestion-%s.log" % PROJECT_NAME

LOG_DIR = PROJECT_DIR if DEBUG else "/var/log/"
LOG_FILE = join(LOG_DIR, LOG_NAME)  # "/var/log/lax.log"
INGESTION_LOG_FILE = join(LOG_DIR, INGESTION_LOG_NAME)  # "/var/log/lax.log"

# whereever our log files are, ensure they are writable before we do anything else.
def writable(path):
    os.system("touch " + path)
    # https://docs.python.org/2/library/os.html
    assert os.access(path, os.W_OK), "file doesn't exist or isn't writable: %s" % path


[writable(log) for log in [LOG_FILE, INGESTION_LOG_FILE]]

ATTRS = [
    "asctime",
    "created",
    "levelname",
    "message",
    "filename",
    "funcName",
    "lineno",
    "module",
    "pathname",
]
FORMAT_STR = " ".join(["%(" + v + ")s" for v in ATTRS])

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {"()": jsonlogger.JsonFormatter, "format": FORMAT_STR},
        "brief": {"format": "%(levelname)s - %(message)s"},
        "django.server": {
            "()": "django.utils.log.ServerFormatter",
            "format": "[%(server_time)s] %(message)s",
        },
    },
    "handlers": {
        "stderr": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "brief",
        },
        "django.server": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "django.server",
        },
        "lax.log": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": LOG_FILE,
            "formatter": "json",
        },
        # entries go to the lax-ingestion.log file
        "ingestion.log": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": INGESTION_LOG_FILE,
            "formatter": "json",
        },
    },
    "loggers": {
        "": {"handlers": ["stderr", "lax.log"], "level": "INFO", "propagate": True},
        "django.request": {
            "handlers": ["lax.log"],
            "level": "DEBUG",
            "propagate": True,
        },
        "django.server": {
            "handlers": ["django.server"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

module_loggers = [
    "publisher.ejp_ingestor",
    "publisher.ajson_ingestor",
    "publisher.management.commands.import",
    "publisher.management.commands.ingest",
]
logger = {
    "level": "INFO",
    "handlers": ["ingestion.log", "lax.log", "stderr"],
    "propagate": False,  # don't propagate up to root logger
}
LOGGING["loggers"].update(
    dict(list(zip(module_loggers, [logger] * len(module_loggers))))
)

# 5 minutes, 300 seconds by default
CACHE_HEADERS_TTL = cfg("general.cache-headers-ttl", 60 * 5)

# ---

