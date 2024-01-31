import copy
from enum import Enum

import logging
import requests
import time
import datetime
from datetime import datetime, timedelta


from qualtrix import settings, error

log = logging.getLogger(__name__)

# Permisions # read:survey_responses

auth_header = {"X-API-TOKEN": settings.API_TOKEN}


class Participant:
    def __init__(
        self, r_id: str, f_name: str, l_name: str, email: str, lang: str
    ) -> None:
        self.response_id = r_id
        self.first_name = f_name
        self.last_name = l_name
        self.email = email
        self.language = lang


class IBetaSurveyQuestion(Enum):
    TESTER_ID = 1
    TEST_TYPE = 2
    DOCUMENT_MODIFICATION = 4
    IMAGE_MODIFICATION = 5
    SELFIE_TEST_TYPE = 6
    DEVICE_TYPE = 7
    DEVICE_MODEL_APPLE = 8
    DEVICE_MODEL_SAMSUNG = 9
    DEVICE_MODEL_GOOGLE = 10
    FAKE_ID_TYPE = 12
    SPOOF_ARTIFACT_TYPE = 13
    DOCUMENT_TYPE = 15
    SUBJECT_ALTERATIONS = 17
    MASK_TYPE = 18

    def QID_text_list(self, qx_data: dict) -> str or None:
        choice_raw = qx_data.get(f"QID{self.value}", None)
        if choice_raw is None:
            return choice_raw

        # Build list of text responses, assuming the worst case that every choice has a
        # user-entered plaintext response
        responses = []

        for val in choice_raw:
            resp = qx_data.get(f"QID{self.value}_{val}_TEXT", None)
            if resp is not None:
                responses.append(resp)
        return responses

    def QID_text(self, qx_data: dict) -> str or None:
        choice_raw = qx_data.get(f"QID{self.value}", None)
        # Get plaintext responses
        response = qx_data.get(f"QID{self.value}_{choice_raw}_TEXT", None)
        return response

    def QID_label(self, qx_labels: dict) -> str or None:
        return qx_labels.get(f"QID{self.value}", None)

    def __eq__(self, other):
        return self.value == other


def get_participant(survey_id: str, response_id: str):
    header = copy.deepcopy(auth_header)
    header["Accept"] = "application/json"

    logging.info(
        f"Survey, Response -> Participant (SurveyId={survey_id}, Response={response_id})"
    )

    # ResponseId -> Email
    r = requests.get(
        settings.BASE_URL + f"/surveys/{survey_id}/responses/{response_id}",
        headers=auth_header,
        timeout=settings.TIMEOUT,
    )

    response_id_to_participant = r.json()

    if "error" in response_id_to_participant["meta"]:
        raise error.QualtricsError(response_id_to_participant["meta"]["error"])

    participant_str = response_id_to_participant["result"]["values"]
    if participant_str is None:
        raise error.QualtricsError(
            "Participant not found, did they complete the intake survey?"
        )

    f_name = participant_str["QID37_1"]
    l_name = participant_str["QID37_2"]
    email = participant_str["QID37_3"]
    lang = participant_str["userLanguage"]

    return Participant(response_id, f_name, l_name, email, lang)


def create_directory_entry(
    email: str, first_name: str, last_name: str, directory_id: str, mailing_list_id: str
):
    header = copy.deepcopy(auth_header)
    header["Accept"] = "application/json"

    logging.info(f"Creating new directory entry for {email}")

    directory_payload = {
        "firstName": first_name,
        "lastName": last_name,
        "email": email,
        "embeddedData": {
            "RulesConsentID": "test-rules",
            "Date": "test-date",
            "time": "test-time",
            "SurveyswapID": "",
            "utm_source": "test-utmsource",
            "utm_medium": "test-utmmedium",
            "utm_campaign": "test-utmcampaign",
        },
    }

    # Create contact
    r = requests.post(
        settings.BASE_URL
        + f"/directories/{directory_id}/mailinglists/{mailing_list_id}/contacts",
        headers=header,
        params={"includeEmbedded": "true"},
        json=directory_payload,
        timeout=settings.TIMEOUT,
    )

    create_directory_entry_response = r.json()
    if "error" in create_directory_entry_response["meta"]:
        raise error.QualtricsError(create_directory_entry_response["meta"]["error"])

    directory_entry = create_directory_entry_response.get("result", None)
    if directory_entry is None:
        raise error.QualtricsError("Something went wrong creating the contact")

    return directory_entry


def create_reminder_distribution(
    library_id: str,
    reminder_message_id: str,
    distribution_id: str,
    reminder_date: datetime,
):

    header = copy.deepcopy(auth_header)
    header["Accept"] = "application/json"

    logging.info(
        f"Create reminder distribution for {distribution_id} on {reminder_date}"
    )

    create_reminder_distribution_payload = {
        "message": {"libraryId": library_id, "messageId": reminder_message_id},
        "header": {
            "fromEmail": settings.FROM_EMAIL,
            "replyToEmail": settings.REPLY_TO_EMAIL,
            "fromName": settings.FROM_NAME,
            "subject": settings.REMINDER_SUBJECT,
        },
        "embeddedData": {"property1": "string", "property2": "string"},
        "sendDate": reminder_date.isoformat() + "Z",
    }

    r = requests.post(
        settings.BASE_URL + f"/distributions/{distribution_id}/reminders",
        headers=header,
        json=create_reminder_distribution_payload,
        timeout=settings.TIMEOUT,
    )

    create_reminder_distribution_response = r.json()
    if "error" in create_reminder_distribution_response["meta"]:
        raise error.QualtricsError(
            create_reminder_distribution_response["meta"]["error"]
        )

    reminder_distribution = create_reminder_distribution_response["result"]
    if reminder_distribution is None:
        raise error.QualtricsError("Something went wrong creating the distribution")

    return reminder_distribution


def add_participant_to_contact_list(
    survey_label: str, survey_link: str, contact_id: str
):
    header = copy.deepcopy(auth_header)
    header["Accept"] = "application/json"

    logging.info("Add participant to the contact list")

    add_particpant_payload = {"embeddedData": {survey_label: survey_link}}

    r = requests.put(
        settings.BASE_URL
        + f"/directories/{settings.DIRECTORY_ID}/mailinglists/{settings.MAILING_LIST_ID}/contacts/{contact_id}",
        headers=header,
        json=add_particpant_payload,
        timeout=settings.TIMEOUT,
    )

    add_to_contact_list_response = r.json()
    if "error" in add_to_contact_list_response["meta"]:
        raise error.QualtricsError(add_to_contact_list_response["meta"]["error"])

    return contact_id


def create_email_distribution(
    contact_id: str,
    library_id: str,
    message_id: str,
    mailing_list_id: str,
    survey_id: str,
):
    header = copy.deepcopy(auth_header)
    header["Accept"] = "application/json"

    logging.info(f"Create email distribution ")

    calltime = datetime.utcnow()
    create_distribution_payload = {
        "message": {"libraryId": library_id, "messageId": message_id},
        "recipients": {"mailingListId": mailing_list_id, "contactId": contact_id},
        "header": {
            "fromEmail": settings.FROM_EMAIL,
            "replyToEmail": settings.REPLY_TO_EMAIL,
            "fromName": settings.FROM_NAME,
            "subject": settings.INVITE_SUBJECT,
        },
        "surveyLink": {
            "surveyId": survey_id,
            "expirationDate": (calltime + timedelta(minutes=5)).isoformat()
            + "Z",  # 1 month
            "type": "Individual",
        },
        "embeddedData": {"": ""},  # for some reason this is required
        "sendDate": (calltime + timedelta(seconds=10)).isoformat() + "Z",
    }

    r = requests.post(
        settings.BASE_URL + f"/distributions",
        headers=header,
        json=create_distribution_payload,
        timeout=settings.TIMEOUT,
    )

    create_distribution_response = r.json()
    if "error" in create_distribution_response["meta"]:
        raise error.QualtricsError(create_distribution_response["meta"]["error"])

    email_distribution = create_distribution_response["result"]
    if email_distribution is None:
        raise error.QualtricsError("Something went wrong creating the distribution")

    return email_distribution


def get_email(survey_id: str, response_id: str):
    header = copy.deepcopy(auth_header)
    header["Accept"] = "application/json"

    logging.info(
        f"Survey, Response -> Email (SurveyId={survey_id}, Response={response_id})"
    )

    # ResponseId -> Email
    r = requests.get(
        settings.BASE_URL + f"/surveys/{survey_id}/responses/{response_id}",
        headers=auth_header,
        timeout=settings.TIMEOUT,
    )

    response_id_to_email = r.json()

    if "error" in response_id_to_email["meta"]:
        raise error.QualtricsError(response_id_to_email["meta"]["error"])

    email = response_id_to_email["result"]["values"].get("QID37_3", None)
    if email is None:
        raise error.QualtricsError(
            "Email could not be found, and redirect link could not be generated"
        )

    return email


def get_contact(directory_id: str, email: str):
    header = copy.deepcopy(auth_header)
    header["Accept"] = "application/json"

    # Email -> Contact ID
    email_to_contact_payload = {
        "filter": {"filterType": "email", "comparison": "eq", "value": email}
    }

    logging.info(f"Email -> Contact (DirectoryId={directory_id})")

    r = requests.post(
        settings.BASE_URL + f"/directories/{directory_id}/contacts/search",
        headers=header,
        params={"includeEmbedded": "true"},
        json=email_to_contact_payload,
        timeout=settings.TIMEOUT,
    )

    email_to_contact_resp = r.json()

    if "error" in email_to_contact_resp["meta"]:
        raise error.QualtricsError(email_to_contact_resp["meta"]["error"])

    contact = next(iter(x for x in email_to_contact_resp["result"]["elements"]), None)
    if contact is None:
        raise error.QualtricsError(
            "Contact ID could not be found, and redirect link could not be generated"
        )

    return contact


def get_distribution(directory_id: str, contact_id: str):
    header = copy.deepcopy(auth_header)
    header["Accept"] = "application/json"

    logging.info(
        f"Directory, Contact -> Distribution (Directory={directory_id}, Contact={contact_id})"
    )
    # Contact ID -> Distribution ID https://api.qualtrics.com/f30cf65c90b7a-get-directory-contact-history
    r = requests.get(
        settings.BASE_URL
        + f"/directories/{directory_id}/contacts/{contact_id}/history",
        headers=header,
        params={"type": "email"},
        timeout=settings.TIMEOUT,
    )

    contact_to_distribution_resp = r.json()

    if "error" in contact_to_distribution_resp["meta"]:
        raise error.QualtricsError(contact_to_distribution_resp["meta"]["error"])

    distribution = next(
        iter(
            [
                x
                for x in contact_to_distribution_resp["result"]["elements"]
                if x["type"] == "Invite"
            ]
        ),
        None,
    )

    if distribution is None:
        raise error.QualtricsError(
            "Distribution ID could not be found, and redirect link could not be generated"
        )

    return distribution


def get_link(target_survey_id: str, distribution_id: str):
    header = copy.deepcopy(auth_header)
    header["Accept"] = "application/json"

    logging.info(
        f"Target Survey, Distribution -> Redirect link (SurveyId={target_survey_id}, Response={distribution_id})"
    )

    # Distribution ID -> Link https://api.qualtrics.com/437447486af95-list-distribution-links
    r = requests.get(
        settings.BASE_URL + f"/distributions/{distribution_id}/links",
        headers=header,
        params={"surveyId": target_survey_id},
        timeout=settings.TIMEOUT,
    )

    distribution_to_link_resp = r.json()

    if "error" in distribution_to_link_resp["meta"]:
        raise error.QualtricsError(distribution_to_link_resp["meta"]["error"])

    link = next(iter(x for x in distribution_to_link_resp["result"]["elements"]), None)
    if link is None:
        raise error.QualtricsError("Link was not yet populated")

    return link


def get_response(survey_id: str, response_id: str):
    for i in range(settings.RETRY_ATTEMPTS):
        r = requests.get(
            settings.BASE_URL + f"/surveys/{survey_id}/responses/{response_id}",
            headers=auth_header,
            timeout=settings.TIMEOUT,
        )
        if r:
            break
        else:
            log.warn(f"Response from id {response_id} not found, trying again.")
        time.sleep(settings.RETRY_WAIT)

    survey_answers = {"status": "", "response": {}}

    response = r.json()

    if (
        r.status_code != 200
        or not response
        or not response["meta"]["httpStatus"] == "200 - OK"
    ):
        raise error.QualtricsError("Survey response not found")

    result = response["result"]
    values = result["values"]

    # Assign survey response status
    # Qualtrics API returns poorly documented boolean as string - unsure if it returns anything else
    survey_answers["status"] = "Complete" if values["finished"] else "Incomplete"

    answer = None

    try:
        answer = get_answer_from_result(result)
    except KeyError as e:
        log.exception(e)
        answer = result

    survey_answers["response"] = answer

    return survey_answers


def get_survey_schema(survey_id: str):
    r = requests.get(
        settings.BASE_URL + f"/surveys/{survey_id}/response-schema",
        headers=auth_header,
        timeout=settings.TIMEOUT,
    )

    return r.json()


def result_export(survey_id: str):
    r_body = {
        "format": "json",
        "compress": False,
        "sortByLastModifiedDate": True,
    }

    r = requests.post(
        settings.BASE_URL + f"/surveys/{survey_id}/export-responses",
        headers=auth_header,
        json=r_body,
        timeout=settings.TIMEOUT,
    )

    if r.status_code != 200:
        return

    progress_id = r.json()["result"]["progressId"]

    while True:
        r = requests.get(
            settings.BASE_URL + f"/surveys/{survey_id}/export-responses/{progress_id}",
            headers=auth_header,
            timeout=settings.TIMEOUT,
        )
        status = r.json()["result"]["status"]

        if status == "complete":
            file_id = r.json()["result"]["fileId"]
            break
        if status == "failed":
            break
        if status == "inProgress":
            time.sleep(1)

    r = requests.get(
        settings.BASE_URL + f"/surveys/{survey_id}/export-responses/{file_id}/file",
        headers=auth_header,
        timeout=settings.TIMEOUT,
    )

    results = r.json()["responses"]
    answers = []
    for result in results:
        try:
            answer = get_answer_from_result(result)
            answers.append(answer)
        except KeyError:
            pass

    return answers


def delete_session(survey_id: str, session_id: str):
    """
    POST /surveys/{surveyId}/sessions/{sessionId}
    body {
        "close": "true"
    }
    """
    r_body = {"close": "true"}

    url = settings.BASE_URL + f"/surveys/{survey_id}/sessions/{session_id}"
    r = requests.post(url, headers=auth_header, json=r_body, timeout=settings.TIMEOUT)

    return r.json()


def get_answer_from_result(result):
    """
    Helper function to get desired values from a result
    """
    labels = result["labels"]
    values = result["values"]

    # Data sometimes has labels missing, so return null if val isnt found
    if values.get("survey_type", None) == "quality_test":
        # Device type -> values returns the integer choice of the user. Casting that to the Enum
        # will convert to one of the specific device types (Apple, Google, Samsung)
        device_type_choice = IBetaSurveyQuestion.DEVICE_TYPE.QID_label(values)
        device_response = {
            "device_group": IBetaSurveyQuestion.DEVICE_TYPE.QID_label(labels),
            "device_model": None,
            # If the user has "Other" device group, (not Apple, Google, or Samsung) the
            # self identification field will be here
            "device_details": IBetaSurveyQuestion.DEVICE_TYPE.QID_text(values),
        }

        if device_type_choice == 1:  # Iphone or Ipad
            device_response[
                "device_model"
            ] = IBetaSurveyQuestion.DEVICE_MODEL_APPLE.QID_label(labels)
            device_response[
                "device_details"
            ] = IBetaSurveyQuestion.DEVICE_MODEL_APPLE.QID_text(values)
        elif device_type_choice == 2:  # Samsung Galaxy Phone or Tablet
            device_response[
                "device_model"
            ] = IBetaSurveyQuestion.DEVICE_MODEL_SAMSUNG.QID_label(labels)
            device_response[
                "device_details"
            ] = IBetaSurveyQuestion.DEVICE_MODEL_SAMSUNG.QID_text(values)
        elif device_type_choice == 3:  # Google Phone or Tablet
            device_response[
                "device_model"
            ] = IBetaSurveyQuestion.DEVICE_MODEL_GOOGLE.QID_label(labels)
            device_response[
                "device_details"
            ] = IBetaSurveyQuestion.DEVICE_MODEL_GOOGLE.QID_text(values)

        return {
            "tester_id": IBetaSurveyQuestion.TESTER_ID.QID_label(labels),
            "test_type": IBetaSurveyQuestion.TEST_TYPE.QID_label(labels),
            "document_modification": {
                "modifications": IBetaSurveyQuestion.DOCUMENT_MODIFICATION.QID_label(
                    labels
                ),
                "descriptions": IBetaSurveyQuestion.DOCUMENT_MODIFICATION.QID_text_list(
                    values
                ),
            },
            "image_modification": IBetaSurveyQuestion.IMAGE_MODIFICATION.QID_label(
                labels
            ),
            "selfie_test_type": IBetaSurveyQuestion.SELFIE_TEST_TYPE.QID_label(labels),
            "device": device_response,
            "fake_id_type": IBetaSurveyQuestion.FAKE_ID_TYPE.QID_label(labels),
            "spoof_artifact_type": IBetaSurveyQuestion.SPOOF_ARTIFACT_TYPE.QID_label(
                labels
            ),
            "document_type": IBetaSurveyQuestion.DOCUMENT_TYPE.QID_label(labels),
            "subject_alteration": {
                "alterations": IBetaSurveyQuestion.SUBJECT_ALTERATIONS.QID_label(
                    labels
                ),
                "descriptions": IBetaSurveyQuestion.SUBJECT_ALTERATIONS.QID_text_list(
                    values
                ),
            },
            "mask": {
                "type": IBetaSurveyQuestion.MASK_TYPE.QID_label(labels),
                "description": IBetaSurveyQuestion.MASK_TYPE.QID_text(values),
            },
        }
    else:
        return {
            "rules_consent_id": values.get("RulesConsentID", None),
            "ethnicity": labels.get("QID12", None),
            "race": labels.get("QID36", None),
            "gender": labels.get("QID14", None),
            "age": values.get("QID15_TEXT", None),
            "income": labels.get("QID24", None),
            "education": labels.get("QID25", None),
            "skin_tone": labels.get("QID67", None),
            "image_redacted_request": labels.get("QID53", None),
            "comments": values.get("QID38_TEXT", None),
        }
