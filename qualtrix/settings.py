"""
Configuration for the qualtrix microservice settings.
Context is switched based on if the app is in debug mode.
"""
import json
import logging
import os

log = logging.getLogger(__name__)


# SECURITY WARNING: don't run with debug turned on in production!
# DEBUG set is set to True if env var is "True"
DEBUG = os.getenv("DEBUG", "False") == "True"

LOG_LEVEL = os.getenv("LOG_LEVEL", logging.getLevelName(logging.INFO))

# Qualtrics API Access
API_TOKEN = None
BASE_URL = None

# Qualtrics API Control
DIRECTORY_ID = None
LIBRARY_ID = None
REMINDER_MESSAGE_ID = None
INVITE_MESSAGE_ID = None
MAILING_LIST_ID = None

# Distribution Content Config
FROM_EMAIL = None
REPLY_TO_EMAIL = None
FROM_NAME = None

INVITE_SUBJECT = None
REMINDER_SUBJECT = None
SURVEY_LINK_TYPE = None


try:
    vcap_services = os.getenv("VCAP_SERVICES")
    config = {}
    if vcap_services:
        user_services = json.loads(vcap_services)["user-provided"]
        for service in user_services:
            if service["name"] == "qualtrix":
                log.info("Loading credentials from env var")
                config = service["credentials"]
                break
        API_TOKEN = config["api_token"]
        BASE_URL = config["base_url"]
        DIRECTORY_ID = config["directory_id"]
        LIBRARY_ID = config["library_id"]
        REMINDER_MESSAGE_ID = config["reminder_message_id"]
        INVITE_MESSAGE_ID = config["invite_message_id"]
        MAILING_LIST_ID = config["mailing_list_id"]
        FROM_EMAIL = config["from_email"]
        REPLY_TO_EMAIL = config["reply_to_email"]
        FROM_NAME = config["from_name"]
        INVITE_SUBJECT = config["invite_subject"]
        REMINDER_SUBJECT = config["reminder_subject"]
        SURVEY_LINK_TYPE = config["survey_link_type"]
        DEMOGRAPHICS_SURVEY_LABEL = config["demographics_survey_label"]
        RULES_CONSENT_ID_LABEL = config["rules_consent_id_label"]

    else:
        API_TOKEN = os.getenv("QUALTRIX_API_TOKEN")
        BASE_URL = os.getenv("QUALTRIX_BASE_URL")
        DIRECTORY_ID = os.getenv("QUALTRIX_DIRECTORY_ID")
        LIBRARY_ID = os.getenv("QUALTRIX_LIBRARY_ID")
        REMINDER_MESSAGE_ID = os.getenv("QUALTRIX_REMINDER_MESSAGE_ID")
        INVITE_MESSAGE_ID = os.getenv("QUALTRIX_INVITE_MESSAGE_ID")
        MAILING_LIST_ID = os.getenv("QUALTRIX_MAILING_LIST_ID")
        FROM_EMAIL = os.getenv("QUALTRIX_FROM_EMAIL")
        REPLY_TO_EMAIL = os.getenv("QUALTRIX_REPLY_TO_EMAIL")
        FROM_NAME = os.getenv("QUALTRIX_FROM_NAME")
        INVITE_SUBJECT = os.getenv("QUALTRIX_INVITE_SUBJECT")
        REMINDER_SUBJECT = os.getenv("QUALTRIX_REMINDER_SUBJECT")
        SURVEY_LINK_TYPE = os.getenv("QUALTRIX_SURVEY_LINK_TYPE")
        DEMOGRAPHICS_SURVEY_LABEL = os.getenv("QUALTRIX_DEMOGRAPHICS_SURVEY_LABEL")
        RULES_CONSENT_ID_LABEL = os.getenv("QUALTRIX_GET_RULES_CONSENT_ID_LABEL")

except (json.JSONDecodeError, KeyError, FileNotFoundError) as err:
    log.warning("Unable to load credentials from VCAP_SERVICES")
    log.debug("Error: %s", str(err))

RETRY_ATTEMPTS = 5
RETRY_WAIT = 2
TIMEOUT = 5
