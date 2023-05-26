"""
Main file to startup the fastapi server.
"""
import sys
import typing

import asyncpg
import sentry_sdk
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi_pagination import add_pagination
from loguru import logger
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.middleware.cors import CORSMiddleware

from jobbergate_api import __version__
from jobbergate_api.apps.job_script_templates.routers import router as job_script_templates_router
from jobbergate_api.apps.job_scripts.routers import router as job_scripts_router
from jobbergate_api.apps.job_submissions.routers import router as job_submissions_router
from jobbergate_api.config import settings
from jobbergate_api.storage import handle_fk_error

subapp = FastAPI(
    title="Jobbergate-API",
    version=__version__,
    contact={
        "name": "Omnivector Solutions",
        "url": "https://www.omnivector.solutions/",
        "email": "info@omnivector.solutions",
    },
    license_info={
        "name": "MIT License",
        "url": "https://github.com/omnivector-solutions/jobbergate/blob/main/LICENSE",
    },
)

subapp.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.SENTRY_DSN and settings.DEPLOY_ENV.lower() != "test":
    logger.info("Initializing Sentry")
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        sample_rate=typing.cast(float, settings.SENTRY_SAMPLE_RATE),  # The cast silences mypy
        environment=settings.DEPLOY_ENV,
    )
    subapp.add_middleware(SentryAsgiMiddleware)
else:
    logger.info("Skipping Sentry")

subapp.include_router(job_script_templates_router)
subapp.include_router(job_scripts_router)
subapp.include_router(job_submissions_router)
subapp.exception_handler(asyncpg.exceptions.ForeignKeyViolationError)(handle_fk_error)

add_pagination(subapp)


@subapp.get(
    "/health",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "API is healthy"}},
)
async def health_check():
    """
    Provide a health-check endpoint for the app.
    """
    logger.debug("CHECKING HEALTH")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


app = FastAPI()
app.mount("/jobbergate", subapp)


@app.on_event("startup")
def init_logger():
    """
    Initialize logging.
    """
    logger.remove()
    logger.add(sys.stderr, level=settings.LOG_LEVEL)
    logger.info(f"Logging configured 📝 Level: {settings.LOG_LEVEL}")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, err: RequestValidationError):
    """
    Handle exceptions from pydantic validators.
    """
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Validation error for request to {request.url} with data: {request.json()}: {err}",
    )
