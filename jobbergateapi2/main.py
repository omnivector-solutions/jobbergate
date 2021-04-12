"""
Main file to startup the fastapi server
"""
from fastapi import FastAPI
from mangum import Mangum

from jobbergateapi2 import storage
from jobbergateapi2.routers import load_routers

app = FastAPI()
load_routers(app)


@app.on_event("startup")
async def init_database():
    """
    Connect the database; create it if necessary
    """
    storage.create_all_tables()
    await storage.database.connect()


@app.on_event("shutdown")
async def disconnect_database():
    """
    Disconnect the database
    """
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
