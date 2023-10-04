import io
import json
import snick
import pendulum
from pyinstrument import Profiler
from pyinstrument.renderers.html import HTMLRenderer
from pyinstrument.renderers.speedscope import SpeedscopeRenderer
from pyinstrument.renderers import JSONRenderer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
from starlette.requests import Request

from jobbergate_api.config import settings
from jobbergate_api.apps.dependencies import s3_bucket


async def fetch_and_reset_body(request: Request):
    """
    Reset the body on the request after fetching it in the middleware.

    See: https://stackoverflow.com/a/73464007
    """
    body = await request.body()
    async def receive() -> Message:
        return {'type': 'http.request', 'body': body}
    request._receive = receive
    return body



class ProfilerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):

        if not settings.PROFILING_ENABLED or not request.query_params.get("profile", False):
            return await call_next(request)

        try:
            body = await fetch_and_reset_body(request)
        except Exception as err:
            body = ""

        with Profiler(interval=0.001, async_mode="enabled") as profiler:
            result = await call_next(request)

        timestamp = pendulum.now().format("YYYYMMDD--hhmmss.SSS")

        async with s3_bucket(settings.S3_PROFILE_BUCKET_NAME, settings.S3_ENDPOINT_URL) as bucket:
            json_key = f"profile.{timestamp}.json"
            json_obj = io.BytesIO(profiler.output(renderer=JSONRenderer()).encode())
            await bucket.upload_fileobj(Fileobj=json_obj, Key=json_key)

            speedscope_key = f"profile.{timestamp}.speedscope.json"
            speedscope_obj = io.BytesIO(profiler.output(renderer=SpeedscopeRenderer()).encode())
            await bucket.upload_fileobj(Fileobj=speedscope_obj, Key=speedscope_key)

            html_key = f"profile.{timestamp}.html"
            html_obj = io.BytesIO(profiler.output(renderer=HTMLRenderer()).encode())
            await bucket.upload_fileobj(Fileobj=html_obj, Key=html_key)

            metadata_key = f"profile.{timestamp}.metadata.txt"
            metadata_obj = io.BytesIO(
                snick.dedent(
                    f"""
                    URL: {request.url}
                    METHOD: {request.method}
                    HEADERS: {request.headers}
                    BODY: {body}
                    """
                ).encode()
            )
            await bucket.upload_fileobj(Fileobj=metadata_obj, Key=metadata_key)

        return result
