import logging
import requests
import time
import re
import json

from qualtrix import settings, error

log = logging.getLogger(__name__)

# Permisions # read:survey_responses

auth_header = {"X-API-TOKEN": settings.API_TOKEN}
application_header = {
    "X-API-TOKEN": settings.API_TOKEN,
    "content-type": "application/json",
}


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


def validate_email(email: str, directory_id=settings.DIRECTORY_ID):
    r = requests.post(
        settings.BASE_URL
        + f"/directories/{directory_id}/contacts/search?includeEmbedded=true&includeSegments=false",
        headers=application_header,
        json=({"filter": {"filterType": "email", "comparison": "eq", "value": email}}),
    )

    if r.status_code != 200:
        raise error.QualtricsError("Survey response not found, likely bad POOL ID")

    elements = list((dict(r.json())["result"]["elements"]))
    return len(elements) != 0


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
        return {
            "tester_id": labels.get("QID1", None),
            "test_type": labels.get("QID2", None),
            "document_modification": labels.get("QID4", None),
            "image_modification": labels.get("QID5", None),
            "selfie_test_type": labels.get("QID6", None),
            "device_type": labels.get("QID7", None),
            "device_model": labels.get("QID8", "")
            + labels.get("QID9", "")
            + labels.get("QID10", "")
            + values.get("QID11_TEXT", ""),
            "fake_id_type": labels.get("QID12", None),
            "spoof_artifact_type": labels.get("QID13", None),
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
