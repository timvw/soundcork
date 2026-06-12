"""Unhandled Exception logger

Attempts to parse the unhandled exceptions in order to produce both a log message and a
pretty-printed set of files that include as much of the context for the request as we
can provide.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from fastapi import Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response as StarletteResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    force=True,
)
logger = logging.getLogger("unhandled.dump")


class NotFoundHandler:
    """
    If enabled, logs unhandled errors.

    Log only requests that are intended for the synthetic Bose server replacements,
    not requests native to Soundcork (eg. HTML pages, OpenAPI docs).
    """

    def __init__(self, log_dir: str) -> None:
        if log_dir:
            self._logging = True
            self._log_root = Path(log_dir)
            # separate folders for each kind of raw log (marge vs. non-marge)
            self._log_dir_marge = self._log_root / "unhandled_raw/marge"
            self._log_dir_other = self._log_root / "unhandled_raw/other"
            self._log_dir_marge.mkdir(parents=True, exist_ok=True)
            self._log_dir_other.mkdir(parents=True, exist_ok=True)
        else:
            self._logging = False

    def _safe(self, s: str, max_len: int = 120) -> str:
        s = re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")
        return s[:max_len] or "x"

    def _is_probably_text(self, body: bytes) -> bool:
        if b"\x00" in body:
            return False
        try:
            body.decode("utf-8")
            return True
        except Exception:
            return False

    def _guess_ext(self, headers: dict, body: bytes) -> str:
        ct = (headers.get("content-type") or "").lower()
        if "xml" in ct:
            return ".xml"
        if "json" in ct:
            return ".json"
        if "text/" in ct:
            return ".txt"
        if self._is_probably_text(body):
            txt = body.decode("utf-8", errors="ignore").lstrip()
            if txt.startswith("<?xml") or txt.startswith("<"):
                return ".xml"
            return ".txt"
        return ".bin"

    def _atomic_write_bytes(self, path: Path, data: bytes) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)

    def _atomic_write_text(self, path: Path, text: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)

    def _dump_request(self, log_dir: Path, prefix: str, request: Request, body: bytes) -> tuple[Path, Path]:
        headers = dict(request.headers)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        ip = request.client.host if request.client else "unknown"
        port = request.client.port if request.client else None
        method = request.method.upper()
        path_part = self._safe(request.url.path.lstrip("/"))

        base = f"{ts}__{self._safe(ip)}__{method}__{path_part}"
        if prefix:
            base = f"{prefix}__{base}"

        meta_path = log_dir / f"{base}.meta.json"
        body_path = log_dir / f"{base}.body"  # raw 1:1
        pretty_path = log_dir / f"{base}.body{self._guess_ext(headers, body)}"

        meta = {
            "timestamp": datetime.now().isoformat(),
            "client": {"host": ip, "port": port},
            "method": method,
            "url": str(request.url),
            "path": request.url.path,
            "query": dict(request.query_params),
            "headers": headers,
            "body_len": len(body),
        }

        self._atomic_write_text(meta_path, json.dumps(meta, ensure_ascii=False, indent=2))
        self._atomic_write_bytes(body_path, body)

        if self._is_probably_text(body):
            self._atomic_write_text(pretty_path, body.decode("utf-8", errors="replace"))

        return meta_path, body_path

    async def dump_unhandled_requests(self, request: Request, exc: StarletteHTTPException) -> StarletteResponse:
        if self._logging:
            if exc.status_code == 404:
                path = request.url.path

                # Case 1: /marge...
                if path.startswith("/marge"):
                    log_dir = self._log_dir_marge
                else:
                    log_dir = self._log_dir_other

                body = await request.body()
                meta_path, body_path = self._dump_request(log_dir, "", request, body)
                logger.warning(
                    "UNHANDLED 404 dumped: %s %s",
                    meta_path.name,
                    body_path.name,
                )

        return StarletteResponse(
            content=str(exc.detail) if exc.detail else "Not Found",
            status_code=exc.status_code,
        )
