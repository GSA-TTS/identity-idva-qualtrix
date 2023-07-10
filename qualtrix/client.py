import logging
import requests
import time
import re
import json

from qualtrix import settings, error

log = logging.getLogger(__name__)

# Permisions # read:survey_responses

auth_header = {"X-API-TOKEN": settings.API_TOKEN}


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
    except KeyError:
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

    skin_tone = labels["QID67"]

    if skin_tone != "Prefer not to answer":
        # searches for alt="{value} - *"
        pattern = rf"alt\s*=\s*['\"](.*?)(\s-)"
        match = re.search(pattern, skin_tone, re.IGNORECASE)

        if match:
            skin_tone = match.group(1)

    return {
        "ethnicity": labels["QID12"],
        "race": labels["QID36"],
        "gender": labels["QID14"],
        "age": values["QID15_TEXT"],
        "income": labels["QID24"],
        "education": labels["QID25"],
        "browser": values["QID17_BROWSER"],
        "version": values["QID17_VERSION"],
        "os": values["QID17_OS"],
        "resolution": values["QID17_RESOLUTION"],
        "skin_tone": skin_tone,
        "image_redacted_request": labels["QID53"],
    }
