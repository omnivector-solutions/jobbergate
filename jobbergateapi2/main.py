"""
Main file to startup the fastapi server
"""
from fastapi import FastAPI
from gino.ext.starlette import Gino
from mangum import Mangum

from .config import settings
from .routers import load_routers

db = Gino()
app = FastAPI()
load_routers(app)


@app.on_event("startup")
async def init_database():
    """
    Connect the database; create it if necessary
    """
    db.config["dsn"] = settings.DATABASE_URL
    db.init_app(app)


def handler(event, context):
    """
    Adapt inbound ASGI requests (from API Gateway) using Mangum
    - Assumes non-ASGI requests (from any other source) are a cloudwatch ping
    """
    if not event.get("requestContext"):
        return

    mangum = Mangum(app)
    return mangum(event, context)
