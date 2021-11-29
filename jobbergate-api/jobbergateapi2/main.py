"""
Main file to startup the fastapi server
"""
import ast

import sentry_sdk
from fastapi import FastAPI, Response, status
from loguru import logger
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.middleware.cors import CORSMiddleware

from jobbergateapi2 import storage
from jobbergateapi2.apps.applications.routers import router as applications_router
from jobbergateapi2.apps.job_scripts.routers import router as job_scripts_router
from jobbergateapi2.apps.job_submissions.routers import router as job_submissions_router
from jobbergateapi2.config import settings

subapp = FastAPI()
subapp.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in ast.literal_eval(settings.BACKEND_CORS_ORIGINS)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.SENTRY_DSN:
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=settings.SENTRY_SAMPLE_RATE)
    subapp.add_middleware(SentryAsgiMiddleware)

subapp.include_router(applications_router)
subapp.include_router(job_scripts_router)
subapp.include_router(job_submissions_router)


@subapp.get(
    "/health", status_code=status.HTTP_204_NO_CONTENT, responses={204: {"description": "API is healthy"}},
)
async def health_check():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


app = FastAPI()
app.mount("/jobbergate", subapp)


@app.on_event("startup")
async def init_database():
    """
    Connect the database; create it if necessary
    """
    logger.debug("Initializing database")
    storage.create_all_tables()
    await storage.database.connect()


@app.on_event("shutdown")
async def disconnect_database():
    """
    Disconnect the database
    """
    logger.debug("Disconnecting database")
    await storage.database.disconnect()
