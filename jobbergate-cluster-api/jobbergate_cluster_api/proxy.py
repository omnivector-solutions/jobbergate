"""
Reverse proxy for the per-session ttyd instances.

The web application never talks to a compute node directly: ttyd's HTTP assets and
websocket are proxied through the cluster API, guarded by the session's one-time
password. ttyd is started with ``--base-path`` matching the public route, so its
relative asset and websocket URLs survive proxying unchanged.
"""

import asyncio

import httpx
import websockets
from fastapi import WebSocket
from loguru import logger
from starlette.requests import Request
from starlette.responses import Response
from starlette.websockets import WebSocketDisconnect, WebSocketState

# Hop-by-hop headers must not be forwarded by a proxy
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


async def proxy_http(endpoint: str, path: str, request: Request) -> Response:
    """Forward a plain HTTP request (the ttyd terminal page and its assets)."""
    url = f"http://{endpoint}{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _HOP_BY_HOP and k.lower() != "host"}
    async with httpx.AsyncClient() as client:
        upstream = await client.request(
            request.method,
            url,
            headers=headers,
            content=await request.body(),
        )
    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in _HOP_BY_HOP}
    return Response(content=upstream.content, status_code=upstream.status_code, headers=response_headers)


async def proxy_websocket(endpoint: str, path: str, client_ws: WebSocket) -> None:
    """
    Bridge the client websocket to the session's ttyd websocket.

    ttyd speaks the ``tty`` subprotocol with binary frames; both directions are pumped
    until either side disconnects.
    """
    url = f"ws://{endpoint}{path}"
    await client_ws.accept(subprotocol="tty")
    try:
        async with websockets.connect(url, subprotocols=["tty"]) as upstream:

            async def client_to_upstream() -> None:
                while True:
                    message = await client_ws.receive()
                    if message["type"] == "websocket.disconnect":
                        break
                    if (data := message.get("bytes")) is not None:
                        await upstream.send(data)
                    elif (text := message.get("text")) is not None:
                        await upstream.send(text)

            async def upstream_to_client() -> None:
                async for data in upstream:
                    if isinstance(data, bytes):
                        await client_ws.send_bytes(data)
                    else:
                        await client_ws.send_text(data)

            done, pending = await asyncio.wait(
                [asyncio.create_task(client_to_upstream()), asyncio.create_task(upstream_to_client())],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
    except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed, OSError) as err:
        logger.debug("Terminal websocket closed: {}", err)
    finally:
        if client_ws.client_state is WebSocketState.CONNECTED:
            await client_ws.close()
