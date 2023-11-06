"""
qualtrix rest api
"""

import logging

import fastapi
from fastapi import HTTPException, responses
from pydantic import BaseModel, typing

from qualtrix import client, error

log = logging.getLogger(__name__)

router = fastapi.APIRouter()


class SurveyModel(BaseModel):
    surveyId: str


class ResponseModel(SurveyModel):
    responseId: str


class SessionModel(SurveyModel):
    sessionId: str


class EmailValidationModel(BaseModel):
    directoryId: str
    email: str


@router.post("/bulk-responses")
async def test():
    return client.result_export()


@router.post("/response")
async def test(request: ResponseModel):
    try:
        return client.get_response(request.surveyId, request.responseId)
    except error.QualtricsError as e:
        raise HTTPException(status_code=400, detail=e.args)


@router.post("/survey-schema")
async def test():
    return client.get_survey_schema()


@router.post("/delete-session")
async def session(request: SessionModel):
    """
    Router for ending a session, pulling response
    """
    try:
        return client.delete_session(request.surveyId, request.sessionId)
    except error.QualtricsError as e:
        raise HTTPException(status_code=400, detail=e.args)


@router.post("/email")
async def email(request: EmailValidationModel):
    """
    Checks if the supplied email exists in the Contact Pool
    """
    try:
        return responses.JSONResponse(
            status_code=200,
            content={
                "emailPresent": client.validate_email(
                    request.email, request.directoryId
                )
            },
        )
    except error.QualtricsError as e:
        raise HTTPException(status_code=422, detail=e.args)
