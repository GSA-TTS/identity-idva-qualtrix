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

API_TOKEN = None
BASE_URL = None
DIRECTORY_ID = None

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
    else:
        API_TOKEN = os.getenv("QX_API_TOKEN")
        BASE_URL = os.getenv("QX_BASE_URL")
        DIRECTORY_ID = os.getenv("QX_DIRECTORY_ID")


except (json.JSONDecodeError, KeyError, FileNotFoundError) as err:
    log.warning("Unable to load credentials from VCAP_SERVICES")
    log.debug("Error: %s", str(err))

RETRY_ATTEMPTS = 5
RETRY_WAIT = 2
TIMEOUT = 5
