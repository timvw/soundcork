import logging
import os

import httpx
from fastapi import APIRouter, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webui", tags=["webui"])

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
SPEAKER_PORT = 8090
SPEAKER_TIMEOUT = 10.0


@router.get("/")
async def webui_index():
    """Serve the web UI single-page application."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# --- Speaker Proxy API ---
# The browser can't directly talk to speakers on the LAN (different origin = CORS).
# These endpoints proxy requests through the soundcork server.


@router.get("/api/speaker/{ip}/{path:path}")
async def proxy_speaker_get(ip: str, path: str):
    """Proxy GET requests to a speaker on the LAN."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"http://{ip}:{SPEAKER_PORT}/{path}",
                timeout=SPEAKER_TIMEOUT,
            )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers={"Content-Type": resp.headers.get("content-type", "text/xml")},
        )
    except httpx.ConnectError:
        return Response(content="Speaker unreachable", status_code=502)
    except httpx.TimeoutException:
        return Response(content="Speaker timeout", status_code=504)


@router.post("/api/speaker/{ip}/{path:path}")
async def proxy_speaker_post(ip: str, path: str, request: Request):
    """Proxy POST requests to a speaker on the LAN."""
    body = await request.body()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://{ip}:{SPEAKER_PORT}/{path}",
                content=body,
                headers={
                    "Content-Type": request.headers.get("content-type", "text/xml")
                },
                timeout=SPEAKER_TIMEOUT,
            )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers={"Content-Type": resp.headers.get("content-type", "text/xml")},
        )
    except httpx.ConnectError:
        return Response(content="Speaker unreachable", status_code=502)
    except httpx.TimeoutException:
        return Response(content="Speaker timeout", status_code=504)


# --- TuneIn Proxy API ---
# Avoids CORS issues when the browser needs to search TuneIn.


@router.get("/api/tunein/{path:path}")
async def proxy_tunein(path: str, request: Request):
    """Proxy GET requests to the TuneIn public API."""
    params = dict(request.query_params)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://opml.radiotime.com/{path}",
                params=params,
                timeout=SPEAKER_TIMEOUT,
            )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            headers={"Content-Type": resp.headers.get("content-type", "text/xml")},
        )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.warning(f"TuneIn proxy error: {e}")
        return Response(content="TuneIn unreachable", status_code=502)
