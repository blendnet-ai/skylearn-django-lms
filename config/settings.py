import os
from decouple import config
from django.utils.translation import gettext_lazy as _
import ssl
from ast import literal_eval

from dotenv import load_dotenv
from attr.converters import to_bool

load_dotenv()

from celery.schedules import crontab

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config(
    "SECRET_KEY", default="o!ld8nrt4vc*h1zoey*wj48x*q0#ss12h=+zh)kk^6b3aygg=!"
)


ALLOWED_HOSTS = [
    "127.0.0.1",
    "4.188.78.208",
    "20.244.100.109",
    "lms.sakshm.com",
    "localhost",
    "orbit-lms.sakshm.com",
]

LOCAL_MEM_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
    }
}

# DEBUG = config("DEBUG", default=False, cast=bool)
DEBUG = os.environ["DEBUG"]
ENV = os.environ["ENV"]

CACHES = LOCAL_MEM_CACHE
if ENV in ["local", "staging"]:
    REDIS_URL = (
        f"redis://{os.environ['REDIS_USER']}:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}/"
        f"{os.environ['REDIS_DB']}"
    )
else:
    REDIS_URL = (
        f"rediss://{os.environ['REDIS_USER']}:{os.environ['REDIS_PASSWORD']}@{os.environ['REDIS_HOST']}:{os.environ['REDIS_PORT']}/"
        f"{os.environ['REDIS_DB']}"
    )

if os.environ.get("REDIS_CACHE_ENABLED", False) == "True":
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "PASSWORD": os.environ["REDIS_PASSWORD"],
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        }
    }

CACHE_TTL = 60 * 60
CACHE_ENABLED = os.environ.get("CACHE_ENABLED", False)

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "default"

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
]

# Third party apps
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "django_filters",
    "django_extensions",
    "django_celery_beat",
    "corsheaders",
    "sass_processor",
]

# Custom apps
PROJECT_APPS = [
    "accounts.apps.AccountsConfig",
    "course.apps.CourseConfig",
    "meetings.apps.MeetingsConfig",
    "reports.apps.ReportsConfig",
    "events_logger.apps.EventsLoggerConfig",
    "notifications_manager.apps.NotificationsManagerConfig",
    "notifications.apps.NotificationsConfig",
    "Feedback.apps.FeedbackConfig",
]


# apps from speechai
INTEGRATED_APPS = [
    "evaluation",
    "ai_learning",
    "data_repo",
    "services",
    "common",
    "OpenAIService",
    "custom_auth",
    "telegram_bot",
]

# Combine all apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS + INTEGRATED_APPS

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.FirebaseAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    #'custom_auth.middleware.OnboardingMiddleware',
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ATOMIC_REQUESTS": True,
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ["POSTGRES_DB"],
        "USER": os.environ["POSTGRES_USER"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        "HOST": os.environ["POSTGRES_HOST"],
        "PORT": os.environ["POSTGRES_PORT"],
    }
}

# https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-DEFAULT_AUTO_FIELD
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/


def gettext(s):
    return s


LANGUAGES = (("en", gettext("English")),)


MODELTRANSLATION_DEFAULT_LANGUAGE = "en"
LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "sass_processor.finders.CssFinder",
]
SASS_PROCESSOR_ROOT = os.path.join(BASE_DIR, "static")


# Media files config
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

VERSION = os.environ.get("VERSION", "VERSION:local-or-error!")

SENTRY_TRACES_SAMPLE_RATE = int(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", 0))

if ENV != "local":
    import sentry_sdk, logging
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration

    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send ERROR and above as events
    )

    sentry_sdk.init(
        dsn=os.environ.get("SENTRY_DSN", ""),
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        integrations=[
            sentry_logging,
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        send_default_pii=True,
        environment=ENV,
        release=VERSION,
    )


# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

if True:
    logging_format = "{asctime}:|{request_id}|user_id={user_id}|{levelname}|{filename}|{lineno}|{message}"
    if DEBUG:
        logging_level = "DEBUG"
    else:
        logging_level = "INFO"
else:
    logging_format = (
        "%(levelname)s [%(request_id)s] user_id=%(user_id)s dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s"
        "%(filename)s %(lineno)d %(message)s"
    )
    logging_level = "INFO"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

# WhiteNoise configuration
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


AI_BOT_USERNAME = os.environ[
    "AI_BOT_USERNAME"
]  ##For staging - "BlendnetAILearningStagingBot"
AI_TELEGRAM_BOT_TOKEN = os.environ["AI_TELEGRAM_BOT_TOKEN"]
DEFAULT_AGENT_CONFIG_NAME = os.environ["DEFAULT_AGENT_CONFIG_NAME"]
ALLOWED_TELEGRAM_USERNAMES = []
BUFFER_DURATION_MINUTES = os.getenv("BUFFER_DURATION_MINUTES", 2)
SPEADSHEET_ID = os.environ["SPEADSHEET_ID"]
TESTS_SUBSHEET_NAME = os.environ["TESTS_SUBSHEET_NAME"]
USERS_SUBSHEET_NAME = os.environ["USERS_SUBSHEET_NAME"]
XOBIN_API_KEY = os.environ["XOBIN_API_KEY"]
XOBIN_ENDPOINT = os.environ["XOBIN_ENDPOINT"]
RESUME_STORAGE_CONTAINER_NAME = os.environ["RESUME_STORAGE_CONTAINER_NAME"]
FIREBASE_API_KEY = os.environ["FIREBASE_API_KEY"]
IDENTITY_TOOLKIT_API_URL = os.environ["IDENTITY_TOOLKIT_API_URL"]
RESUME_APP_BACKEND_URL = os.environ["RESUME_APP_BACKEND_URL"]
GITHUB_API_BASE_URL = os.environ["GITHUB_API_BASE_URL"]
GITHUB_API_TOKEN = os.environ["GITHUB_API_TOKEN"]
ADMIN_FIREBASE_ACCOUNT_ID = os.environ["ADMIN_FIREBASE_ACCOUNT_ID"]
USER_IDS_CODING_TEST_ENABLED = os.environ["USER_IDS_CODING_TEST_ENABLED"]
AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_OPENAI_API_VERSION = os.environ["AZURE_OPENAI_API_VERSION"]
AZURE_OPENAI_AZURE_ENDPOINT = os.environ["AZURE_OPENAI_AZURE_ENDPOINT"]

TEST_EVALUATION_WAITING_TIME_IN_SECONDS = os.environ.get(
    "TEST_EVALUATION_WAITING_TIME_IN_SECONDS", 240
)  # 4 minutes
DSA_FLOW_TEST_QUESTION_ID = os.environ.get("DSA_FLOW_TEST_QUESTION_ID")

AZURE_OPENAI_API_KEY_OLD = os.environ["AZURE_OPENAI_API_KEY_OLD"]
AZURE_OPENAI_AZURE_ENDPOINT_OLD = os.environ["AZURE_OPENAI_AZURE_ENDPOINT_OLD"]

GLOT_KEY = os.environ["GLOT_KEY"]
GLOT_URL = os.environ["GLOT_URL"]

SELF_HOSTED_GLOT_KEY = os.environ["SELF_HOSTED_GLOT_KEY"]
SELF_HOSTED_GLOT_URL = os.environ["SELF_HOSTED_GLOT_URL"]

SENDGRID_API_KEY = os.environ["SENDGRID_API_KEY"]
CREDS_EMAIL_TEMPLATE_ID = os.environ.get("CREDS_EMAIL_TEMPLATE_ID")
PASSWORD_EMAIL_TEMPLATE_ID = os.environ.get("PASSWORD_EMAIL_TEMPLATE_ID")

DSA_GLOBAL_SHEET_ID = os.environ.get("DSA_GLOBAL_SHEET_ID")
DSA_METRICS_SHEET_ID = os.environ.get("DSA_METRICS_SHEET_ID")
BACKEND_BASE_URL = os.environ.get("BACKEND_BASE_URL")

LLM_CONFIGS_PATH = str(BASE_DIR) + "/llm_configs_v2/"
DISABLE_PROMPT_VALIDATIONS = to_bool(
    os.environ.get("DISABLE_PROMPT_VALIDATIONS", "FALSE")
)

import litellm


LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")
LANGFUSE_SAMPLE_RATE = os.environ.get("LANGFUSE_SAMPLE_RATE", 1)

LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com")

if LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY:
    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]

DOUBT_SOLVING_ORG_API_KEY = os.environ.get("DOUBT_SOLVING_ORG_API_KEY")
TELEGRAM_BOT_NAME = os.environ.get("TELEGRAM_BOT_NAME")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TWO_Factor_SMS_API_KEY = os.environ.get("TWO_Factor_SMS_API_KEY")


# Celery Configuration
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = config(
    "CELERY_RESULT_BACKEND", default="redis://localhost:6379/0"
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE  # Use the same timezone as Django

CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# Celery Beat Settings (if you need scheduled tasks)

CELERY_BEAT_SCHEDULE = {
    "check-for-completed-meetings-every-1-hour": {
        "task": "meetings.tasks.process_completed_meetings_task",
        "schedule": crontab(hour="*", minute=0),  # Executes every 1 hour
    },
    "process-activity-aggregations": {
        "task": "reports.tasks.process_aggregation",
        "schedule": crontab(hour=17, minute=30),  # Executes at 5:30 PM UTC (11 PM IST)
    },
    "process-report-aggregations": {
        "task": "reports.tasks.process_reports",
        "schedule": crontab(
            hour=18, minute=0
        ),  # Executes at 6:00 PM UTC (11:30 PM IST)
    },
    "generate-report-sheet": {
        "task": "reports.tasks.generate_report_sheet",
        "schedule": crontab(
            hour=18, minute=15
        ),  # Executes at 6:15 PM UTC (11:45 AM IST)
    },
    "schedule-meeting-notifications": {
        "task": "notifications_manager.tasks.schedule_meeting_notifications_task",
        "schedule": crontab(
            hour=18, minute=35
        ),  #  Executes at 6:35 PM UTC (12:05 AM IST next day)
    },
    "schedule-missed-lecture-notifications": {
        "task": "notifications_manager.tasks.schedule_missed_lecture_notifications_task",
        "schedule": crontab(
            hour=3, minute=30
        ),  # Executes at 6:40 PM UTC (12:10 AM IST next day)
    },
    "schedule-inactive-user-notifications": {
        "task": "notifications_manager.tasks.schedule_inactive_user_notifications_task",
        "schedule": crontab(
            hour=4, minute=30
        ),  # Executes at 6:45 PM UTC (12:15 AM IST next day)
    },
    "schedule-pending-assessments-notifications": {
        "task": "notifications_manager.tasks.schedule_pending_assessments_notifications_task",
        "schedule": crontab(
            hour=4, minute=35
        ),  # Executes at 6:50 PM UTC (12:20 AM IST next day)
    },
    "check-for-pending-intents": {
        "task": "notifications.tasks.process_notification_intents",
        "schedule": crontab(minute="*/5"),  # Runs every 5 minutes
    },
    "check-for-student-status": {
        "task": "accounts.tasks.update_student_status_task",
        "schedule": crontab(
            hour=18, minute=35
        ),  # Executes at 6:00 PM UTC (11:30 PM IST)
    },
    "sync_user_configs": {
        "task": "accounts.tasks.sync_configs_task",
        "schedule": crontab(minute=0),  # Executes every hour at minute 0
    },
}

# Task-specific settings
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes timeout
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # Soft timeout 5 minutes before hard timeout
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_RETRY_DELAY = 300  # 5 minutes


# MS Teams settings
MS_TEAMS_ACCESS_TOKEN_CACHE_KEY = "msteams_access_token"
MS_TEAMS_CLIENT_ID = config("MS_TEAMS_CLIENT_ID")
MS_TEAMS_CLIENT_SECRET = config("MS_TEAMS_CLIENT_SECRET")
MS_TEAMS_TENANT_ID = config("MS_TEAMS_TENANT_ID")
# This Admin user id is needed to be given permissions to create meetings via powershell
# refer to this gpt chat for documentation https://chatgpt.com/share/673f0e30-d540-8007-b07d-a22c9a60fd4a
MS_TEAMS_ADMIN_USER_ID = config("MS_TEAMS_ADMIN_USER_ID")
MS_TEAMS_ADMIN_USER_NAME = config("MS_TEAMS_ADMIN_USER_NAME")
MS_TEAMS_ADMIN_UPN = config("MS_TEAMS_ADMIN_UPN")


STORAGE_ACCOUNT_NAME = os.environ.get("STORAGE_ACCOUNT_NAME", "stspeechaistage")
STORAGE_ACCOUNT_KEY = os.environ.get("STORAGE_ACCOUNT_KEY")

# Firebase Settings
FIREBASE_API_KEY = os.environ["FIREBASE_API_KEY"]
FIREBASE_UNIVERSE_DOMAIN = os.environ["FIREBASE_UNIVERSE_DOMAIN"]
FIREBASE_ENABLED = os.environ.get("FIREBASE_ENABLED") == "TRUE"
FIREBASE_ACCOUNT_TYPE = os.environ.get("FIREBASE_ACCOUNT_TYPE")
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID")
FIREBASE_PRIVATE_KEY_ID = os.environ.get("FIREBASE_PRIVATE_KEY_ID")
FIREBASE_PRIVATE_KEY = os.environ.get("FIREBASE_PRIVATE_KEY")
FIREBASE_CLIENT_EMAIL = os.environ.get("FIREBASE_CLIENT_EMAIL")
FIREBASE_CLIENT_ID = os.environ.get("FIREBASE_CLIENT_ID")
FIREBASE_AUTH_URI = os.environ.get("FIREBASE_AUTH_URI")
FIREBASE_TOKEN_URI = os.environ.get("FIREBASE_TOKEN_URI")
FIREBASE_AUTH_PROVIDER_X509_CERT_URL = os.environ.get("FIREBASE_CLIENT_X509_CERT_URL")
FIREBASE_CLIENT_X509_CERT_URL = os.environ.get("FIREBASE_CLIENT_X509_CERT_URL")
FIREBASE_UNIVERSE_DOMAIN = os.environ.get("UNIVERSE_DOMAIN")
FIREBASE_AUTH_DOMAIN = os.environ["FIREBASE_AUTH_DOMAIN"]
FIREBASE_STORAGE_BUCKET = os.environ["FIREBASE_STORAGE_BUCKET"]
FIREBASE_MESSAGING_SENDER_ID = os.environ["FIREBASE_MESSAGING_SENDER_ID"]
FIREBASE_APP_ID = os.environ["FIREBASE_APP_ID"]
FIREBASE_MEASUREMENT_ID = os.environ["FIREBASE_MEASUREMENT_ID"]


### SERVICE SETTINGS
## WHISPER-TIMESTAMP SERVICE
WHISPER_TIMESTAMP_SERVICE_ENDPOINT = os.environ["WHISPER_TIMESTAMP_SERVICE_ENDPOINT"]
WHISPER_TIMESTAMP_SERVICE_AUTH_TOKEN = os.environ[
    "WHISPER_TIMESTAMP_SERVICE_AUTH_TOKEN"
]

## CEFR_LEVEL_SERVICE
CEFR_LEVEL_SERVICE_ENDPOINT = os.environ["CEFR_LEVEL_SERVICE_ENDPOINT"]
CEFR_LEVEL_SERVICE_AUTH_TOKEN = os.environ["CEFR_LEVEL_TIMESTAMP_SERVICE_AUTH_TOKEN"]

PRONUNCIATION_SERVICE_ENDPOINT = os.environ["PRONUNCIATION_SERVICE_ENDPOINT"]
PRONUNCIATION_SERVICE_AUTH_TOKEN = os.environ["PRONUNCIATION_SERVICE_AUTH_TOKEN"]

AZURE_TEXT_ANALYTICS_CLIENT_KEY = os.environ["AZURE_TEXT_ANALYTICS_CLIENT_KEY"]
AZURE_TEXT_ANALYTICS_CLIENT_ENDPOINT = os.environ[
    "AZURE_TEXT_ANALYTICS_CLIENT_ENDPOINT"
]

DEEPGRAM_KEY = os.environ["DEEPGRAM_KEY"]

ANYMAIL = {
    "SENDGRID_API_KEY": os.environ["SENDGRID_API_KEY"]
    # "MAILJET_API_KEY": os.environ["MAILJET_API_KEY"],
    # "MAILJET_SECRET_KEY": os.environ["MAILJET_SECRET_KEY"],
}

# EMAIL_BACKEND = "anymail.backends.mailjet.EmailBackend"
EMAIL_BACKEND = "anymail.backends.sendgrid.EmailBackend"
DEPLOYMENT_TYPE = os.environ.get("DEPLOYMENT_TYPE", "DEFAULT")
DEFAULT_FROM_EMAIL = (
    "lms.noreply@theearthcarefoundation.org"
    if DEPLOYMENT_TYPE == "ECF"
    else "contact@sakshm.com"
)
SERVER_EMAIL = DEFAULT_FROM_EMAIL

ADMINS = os.environ["ADMINS"]
if ADMINS:
    ADMINS = literal_eval(ADMINS)

REFERRAL_URL = os.environ.get("REFERRAL_URL")
FEEDBACK_FORM_URL = os.environ.get("FEEDBACK_FORM_URL")

# Word of the day cache TTL - 1 day in seconds
WORD_OF_DAY_CACHE_TTL = 86400


CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)


CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

CELERY_TASK_ROUTES = {
    "meetings.tasks.*": {"queue": "meeting_queue"},
    "course.tasks.*": {"queue": "course_queue"},
    "reports.tasks.*": {"queue": "reporting_queue"},
}

CELERY_USE_SSL = not (os.environ.get("CELERY_USE_SSL", "TRUE") == "FALSE")
if CELERY_USE_SSL:
    BROKER_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE}
    CELERY_d_BACKEND_USE_SSL = {"ssl_cert_reqs": ssl.CERT_NONE}

# change the default user models to our custom model
AUTH_USER_MODEL = "accounts.User"
STUDENT_ID_PREFIX = config("STUDENT_ID_PREFIX", "ugr")
LECTURER_ID_PREFIX = config("LECTURER_ID_PREFIX", "lec")


STORAGE_ACCOUNT_KEY = os.environ.get("STORAGE_ACCOUNT_KEY")
RECORDINGS_CONTAINER_NAME = os.environ.get("RECORDINGS_CONTAINER_NAME")
AZURE_STORAGE_COURSE_MATERIALS_CONTAINER_NAME = os.environ.get(
    "AZURE_STORAGE_COURSE_MATERIALS_CONTAINER_NAME"
)
REPORT_SPEADSHEET_ID = os.environ.get("REPORT_SPEADSHEET_ID")
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "https://lms.sakshm.com")

ORBIT_COURSE_CODES = os.environ.get("ORBIT_COURSE_CODES")
TEST_EMAILS = os.environ.get("TEST_EMAILS", [])
REPORT_SPEADSHEET_ID_WITHOUT_TEST_EMAILS = os.environ.get(
    "REPORT_SPEADSHEET_ID_WITHOUT_TEST_EMAILS"
)

MEETING_PROVIDER = os.environ.get("MEETING_PROVIDER", "teams")
# Initialize meeting service
from meetings.services.service_resolver import get_meeting_service

MEETING_SERVICE = get_meeting_service()
ZOOM_API_KEY = os.environ.get("ZOOM_API_KEY", "")
ZOOM_API_SECRET = os.environ.get("ZOOM_API_SECRET", "")
ZOOM_ACCOUNT_ID = os.environ.get("ZOOM_ACCOUNT_ID", "")
ZOOM_ACCESS_TOKEN_CACHE_KEY = "zoom_access_token"
PASSWORD_CC_EMAIL = os.environ.get("PASSWORD_CC_EMAIL", None)
