"""
Main file to startup the fastapi server
"""
from fastapi import FastAPI
from mangum import Mangum
from starlette.middleware.cors import CORSMiddleware

from loguru import logger

from jobbergateapi2 import storage
from jobbergateapi2.config import settings
from jobbergateapi2.routers import load_routers

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def init_database():
    """
    Connect the database; create it if necessary
    """
    logger.debug("Initializing database")
    storage.create_all_tables()
    await storage.database.connect()

    logger.debug("Loading routers")
    load_routers(app)


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
