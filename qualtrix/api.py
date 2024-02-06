"""
qualtrix rest api
"""

from asyncio import create_task
from datetime import datetime, timedelta
import logging
import time
from zoneinfo import ZoneInfo

import fastapi
from fastapi import HTTPException
from pydantic import BaseModel

from qualtrix import client, error, settings

log = logging.getLogger(__name__)

router = fastapi.APIRouter()


class SurveyModel(BaseModel):
    surveyId: str


class ResponseModel(SurveyModel):
    responseId: str


class SessionModel(SurveyModel):
    sessionId: str


class RedirectModel(SurveyModel):
    targetSurveyId: str
    RulesConsentID: str  # Client dependent
    SurveyswapID: str  # Client dependent
    SurveyswapGroup: str  # Client dependent
    utm_campaign: str
    utm_medium: str
    utm_source: str
    email: str
    firstName: str
    lastName: str


@router.post("/bulk-responses")
async def get_bulk_responses(request: SurveyModel):
    return client.result_export(request.surveyId)


@router.post("/response")
async def get_response(request: ResponseModel):
    try:
        return client.get_response(request.surveyId, request.responseId)
    except error.QualtricsError as e:
        raise HTTPException(status_code=400, detail=e.args)


@router.post("/redirect")
async def intake_redirect(request: RedirectModel):
    start_time = time.time()
    try:
        directory_entry = client.create_directory_entry(
            request.email,
            request.firstName,
            request.lastName,
            settings.DIRECTORY_ID,
            settings.MAILING_LIST_ID,
        )

        email_distribution = client.create_email_distribution(
            directory_entry["contactLookupId"],
            settings.LIBRARY_ID,
            settings.INVITE_MESSAGE_ID,
            settings.MAILING_LIST_ID,
            request.targetSurveyId,
        )

        link = client.get_link(request.targetSurveyId, email_distribution["id"])

        # If link creation succeeds, create reminders while the link is returned
        create_task(create_reminder_distributions(email_distribution["id"]))
        create_task(
            add_user_to_contact_list(
                link["link"],
                directory_entry["id"],
                request.RulesConsentID,
                request.SurveyswapID,
                request.SurveyswapGroup,
                request.utm_campaign,
                request.utm_medium,
                request.utm_source,
                request.firstName,
                request.lastName,
                # https://stackoverflow.com/questions/10997577/python-timezone-conversion
                # Consumers to this data require mountain time
                datetime.now(tz=ZoneInfo("MST")),
            )
        )

        log.info("Redirect link created in %.2f seconds" % (time.time() - start_time))
        return link
    except error.QualtricsError as e:
        logging.error(e)
        # the next time any client side changes are required update this to 422
        raise HTTPException(status_code=422, detail=e.args)


async def create_reminder_distributions(distribution_id: str):
    distribution = client.create_reminder_distribution(
        settings.LIBRARY_ID,
        settings.REMINDER_MESSAGE_ID,
        distribution_id,
        (datetime.utcnow() + timedelta(days=1)),
    )

    distribution = client.create_reminder_distribution(
        settings.LIBRARY_ID,
        settings.REMINDER_MESSAGE_ID,
        distribution_id,
        (datetime.utcnow() + timedelta(days=3)),
    )


async def add_user_to_contact_list(
    survey_link: str,
    contact_id: str,
    rules_consent_id: str,
    survey_swap_id: str,
    survey_swap_group: str,
    utm_campaign: str,
    utm_medium: str,
    utm_source: str,
    first_name: str,
    last_name: str,
    timestamp: datetime,
):
    return client.add_participant_to_contact_list(
        settings.DEMOGRAPHICS_SURVEY_LABEL,
        survey_link,
        settings.RULES_CONSENT_ID_LABEL,
        client.modify_prefix("FS", "R", rules_consent_id),
        settings.SURVEY_SWAP_ID_LABEL,
        survey_swap_id,
        settings.SURVEY_SWAP_GROUP_LABEL,
        survey_swap_group,
        contact_id,
        utm_campaign,
        utm_medium,
        utm_source,
        first_name,
        last_name,
        timestamp,
    )


@router.post("/survey-schema")
async def get_schema(request: SurveyModel):
    return client.get_survey_schema(request.surveyId)


@router.post("/delete-session")
async def session(request: SessionModel):
    """
    Router for ending a session, pulling response
    """
    try:
        return client.delete_session(request.surveyId, request.sessionId)
    except error.QualtricsError as e:
        raise HTTPException(status_code=400, detail=e.args)


@router.get("/contact/{contactId}/responseIds")
async def dist(contactId: str):
    return client.get_responseIds_by_contact(contactId)


@router.get("/dist/{distId}/responseIds")
async def dist(distId: str):
    return client.get_responseIds_by_dist(distId)
