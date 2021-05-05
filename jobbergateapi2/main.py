"""
Main file to startup the fastapi server
"""
import aioredis
from fastapi import FastAPI
from fastapi_admin.app import app as admin_app
from fastapi_admin.providers.login import UsernamePasswordProvider
from mangum import Mangum

from jobbergateapi2 import storage
from jobbergateapi2.apps.users.schemas import User
from jobbergateapi2.routers import load_routers

app = FastAPI()
app.mount("/admin", admin_app)
login_provider = UsernamePasswordProvider(admin_model=User)
load_routers(app)


@app.on_event("startup")
async def init_database():
    """
    Connect the database; create it if necessary
    """
    storage.create_all_tables()
    await storage.database.connect()


@app.on_event("startup")
async def startup():
    redis = await aioredis.create_redis_pool(
        "redis://fastapi-admin.4vtu8j.0001.eun1.cache.amazonaws.com", encoding="utf8"
    )
    admin_app.configure(
        logo_url="https://preview.tabler.io/static/logo-white.svg",
        login_logo_url="https://preview.tabler.io/static/logo.svg",
        template_folders=["templates"],
        login_provider=login_provider,
        maintenance=False,
        redis=redis,
    )


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
