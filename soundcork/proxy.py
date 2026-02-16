import json
import logging
import os
import re
from datetime import datetime, timezone

import httpx
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from soundcork.config import Settings

logger = logging.getLogger(__name__)

# Bose server mapping (from /opt/Bose/etc/SoundTouchSdkPrivateCfg.xml)
UPSTREAM_MAP: dict[str, str] = {
    "/marge": "https://streaming.bose.com",
    "/bmx": "https://content.api.bose.io",
    "/updates": "https://worldwide.bose.com",
}

# Hop-by-hop headers that must not be forwarded
HOP_BY_HOP = frozenset(
    {
        "host",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "upgrade",
    }
)


def _match_upstream(path: str) -> tuple[str, str] | None:
    """Return (upstream_base, prefix) if path matches a known Bose prefix."""
    for prefix, upstream in UPSTREAM_MAP.items():
        if path == prefix or path.startswith(prefix + "/"):
            return upstream, prefix
    return None


def _sanitize_path(path: str) -> str:
    """Sanitize a URL path for use in a filename."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", path.strip("/"))[:120]


def _log_exchange(
    log_dir: str,
    method: str,
    path: str,
    query: str,
    req_headers: dict,
    req_body: bytes,
    upstream_url: str,
    status: int,
    resp_headers: dict,
    resp_body: bytes,
) -> None:
    """Write a JSON traffic log file."""
    os.makedirs(log_dir, exist_ok=True)

    now = datetime.now(timezone.utc)
    ts = now.strftime("%Y%m%dT%H%M%S")
    us = f"{now.microsecond:06d}"
    sanitized = _sanitize_path(path)
    filename = f"{ts}_{us}_{method}_{sanitized}.json"

    # Best-effort decode bodies as text; fall back to base64-ish repr
    try:
        req_body_str = req_body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        req_body_str = repr(req_body)

    try:
        resp_body_str = resp_body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        resp_body_str = repr(resp_body)

    entry = {
        "timestamp": now.isoformat(),
        "request": {
            "method": method,
            "path": path,
            "query": query,
            "headers": req_headers,
            "body": req_body_str,
        },
        "upstream_url": upstream_url,
        "response": {
            "status": status,
            "headers": resp_headers,
            "body": resp_body_str,
        },
    }

    filepath = os.path.join(log_dir, filename)
    try:
        with open(filepath, "w") as f:
            json.dump(entry, f, indent=2, default=str)
    except OSError:
        logger.exception("Failed to write traffic log to %s", filepath)


class ProxyMiddleware(BaseHTTPMiddleware):
    """Transparent proxy to real Bose servers.

    When SOUNDCORK_MODE=proxy, requests matching known Bose path prefixes
    are forwarded to the real upstream servers and the full exchange is
    logged.  When SOUNDCORK_MODE=local (the default), all requests pass
    through to soundcork's local handlers.
    """

    def __init__(self, app):
        super().__init__(app)
        self._settings = Settings()

    async def dispatch(self, request: Request, call_next):
        if self._settings.soundcork_mode != "proxy":
            return await call_next(request)

        match = _match_upstream(request.url.path)
        if match is None:
            # Not a known Bose prefix — let local handlers deal with it
            return await call_next(request)

        upstream_base, _prefix = match
        return await self._forward(request, upstream_base)

    async def _forward(self, request: Request, upstream_base: str) -> Response:
        method = request.method
        path = request.url.path
        query = str(request.url.query)
        upstream_url = f"{upstream_base}{path}"
        if query:
            upstream_url = f"{upstream_url}?{query}"

        # Build forwarding headers (strip hop-by-hop)
        fwd_headers = {
            k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP
        }

        req_body = await request.body()

        try:
            async with httpx.AsyncClient() as client:
                upstream_resp = await client.request(
                    method=method,
                    url=upstream_url,
                    headers=fwd_headers,
                    content=req_body,
                    follow_redirects=True,
                )
        except httpx.RequestError:
            logger.exception("Upstream request failed for %s %s", method, upstream_url)
            _log_exchange(
                log_dir=self._settings.soundcork_log_dir,
                method=method,
                path=path,
                query=query,
                req_headers=fwd_headers,
                req_body=req_body,
                upstream_url=upstream_url,
                status=502,
                resp_headers={},
                resp_body=b"Bad Gateway",
            )
            return Response(content="Bad Gateway", status_code=502)

        resp_body = upstream_resp.content
        resp_headers = dict(upstream_resp.headers)

        # Log the full exchange
        _log_exchange(
            log_dir=self._settings.soundcork_log_dir,
            method=method,
            path=path,
            query=query,
            req_headers=fwd_headers,
            req_body=req_body,
            upstream_url=upstream_url,
            status=upstream_resp.status_code,
            resp_headers=resp_headers,
            resp_body=resp_body,
        )

        # Strip content-encoding/content-length since httpx already decoded
        excluded = {"content-encoding", "content-length", "transfer-encoding"}
        return_headers = {
            k: v for k, v in resp_headers.items() if k.lower() not in excluded
        }

        return Response(
            content=resp_body,
            status_code=upstream_resp.status_code,
            headers=return_headers,
        )
