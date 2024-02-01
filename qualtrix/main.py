"""
Qualtrix Microservice FastAPI Web App.
"""
import logging

import fastapi
import starlette_prometheus

from . import api, settings

logging.basicConfig(level=settings.LOG_LEVEL)

app = fastapi.FastAPI()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(starlette_prometheus.PrometheusMiddleware)
app.add_route("/metrics/", starlette_prometheus.metrics)

app.include_router(api.router)
