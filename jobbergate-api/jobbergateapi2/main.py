"""
Main file to startup the fastapi server
"""
import ast

from fastapi import FastAPI
from loguru import logger
from mangum import Mangum
from starlette.middleware.cors import CORSMiddleware

from jobbergateapi2 import storage
from jobbergateapi2.apps.applications.routers import router as applications_router
from jobbergateapi2.apps.job_scripts.routers import router as job_scripts_router
from jobbergateapi2.apps.job_submissions.routers import router as job_submissions_router
from jobbergateapi2.config import settings

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in ast.literal_eval(settings.BACKEND_CORS_ORIGINS)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(applications_router)
app.include_router(job_scripts_router)
app.include_router(job_submissions_router)


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


def handler(event, context):
    """
    Adapt inbound ASGI requests (from API Gateway) using Mangum
    - Assumes non-ASGI requests (from any other source) are a cloudwatch ping
    """
    if not event.get("requestContext"):
        return

    mangum = Mangum(app)
    return mangum(event, context)
