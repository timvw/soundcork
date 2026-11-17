"""Root-level alias routes must respond exactly like the canonical /marge and /bmx routes."""

# Claude: Pin alias routes to the canonical routes' response settings.

from unittest.mock import MagicMock

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import soundcork.main as main
from soundcork.model import DeviceInfo
from soundcork.speaker_allowlist import SpeakerAllowlist

SPEAKER_IP = "192.168.1.143"
INHERITED = (
    "response_class",
    "response_model",
    "status_code",
    "response_model_exclude_none",
    "dependencies",
)


def _routes() -> list[APIRoute]:
    return [r for r in main.app.router.routes if isinstance(r, APIRoute)]


def _is_alias(route: APIRoute) -> bool:
    return any(tag.endswith("-alias") for tag in route.tags or [])


def _alias_pairs() -> list[tuple[APIRoute, APIRoute]]:
    canonical = {}
    for route in _routes():
        if not _is_alias(route):
            canonical.setdefault(route.endpoint, route)
    return [(alias, canonical[alias.endpoint]) for alias in _routes() if _is_alias(alias)]


def _value(setting):
    # FastAPI wraps unset defaults in DefaultPlaceholder; compare what is actually used.
    return getattr(setting, "value", setting)


@pytest.mark.parametrize(
    ("alias", "canonical"),
    _alias_pairs(),
    ids=lambda r: f"{'/'.join(sorted(r.methods))} {r.path}",
)
def test_alias_inherits_canonical_response_settings(alias, canonical):
    for name in INHERITED:
        assert _value(getattr(alias, name)) == _value(getattr(canonical, name)), name


@pytest.fixture
def speaker_client(monkeypatch):
    device = DeviceInfo(
        device_id="AABBCCDDEEFF",
        product_code="SoundTouch 20",
        device_serial_number="SN123",
        product_serial_number="PSN123",
        firmware_version="27.0",
        ip_address=SPEAKER_IP,
        name="Test Speaker",
        created_on="2026-01-01T00:00:00",
        updated_on="2026-01-01T00:00:00",
    )
    ds = MagicMock()
    ds.list_accounts.return_value = ["1234567"]
    ds.list_devices.return_value = [device.device_id]
    ds.get_device_info.return_value = device
    monkeypatch.setattr(main, "_speaker_allowlist", SpeakerAllowlist(ds))
    monkeypatch.setattr(main.settings, "trusted_proxy_ips", "testclient")
    return TestClient(main.app, headers={"X-Forwarded-For": SPEAKER_IP})


def test_alias_serves_bose_xml_not_json_string(speaker_client):
    path = "/streaming/software/update/account/1234567"
    canonical = speaker_client.get("/marge" + path)
    alias = speaker_client.get(path)

    assert canonical.status_code == alias.status_code == 200
    assert alias.headers["content-type"] == canonical.headers["content-type"]
    assert alias.headers["content-type"].startswith("application/vnd.bose.streaming")
    assert alias.text == canonical.text
    assert alias.text.startswith("<?xml")


# Claude: Aliases must also inherit the canonical route's ETag dependency.
def test_alias_serves_etag_and_honours_if_none_match(speaker_client):
    path = "/streaming/software/update/account/1234567"
    canonical = speaker_client.get("/marge" + path)
    alias = speaker_client.get(path)

    assert alias.headers["etag"] == canonical.headers["etag"]

    not_modified = speaker_client.get(path, headers={"If-None-Match": alias.headers["etag"]})
    assert not_modified.status_code == 304
