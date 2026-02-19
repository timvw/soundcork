"""Tests for IP restriction on Bose protocol endpoints and webui SSRF hardening."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from soundcork.model import DeviceInfo
from soundcork.speaker_allowlist import SpeakerAllowlist


def _make_device_info(ip: str, device_id: str = "AABBCCDDEEFF") -> DeviceInfo:
    return DeviceInfo(
        device_id=device_id,
        product_code="SoundTouch 20",
        device_serial_number="SN123",
        product_serial_number="PSN123",
        firmware_version="27.0",
        ip_address=ip,
        name="Test Speaker",
    )


def _make_allowlist(*ips: str) -> SpeakerAllowlist:
    ds = MagicMock()
    ds.list_accounts.return_value = [f"acct{i}" for i in range(len(ips))]
    ds.list_devices.side_effect = [[f"DEV{i:010d}00"] for i in range(len(ips))]
    ds.get_device_info.side_effect = [
        _make_device_info(ip, f"DEV{i:010d}00") for i, ip in enumerate(ips)
    ]
    return SpeakerAllowlist(ds)


@pytest.fixture
def allowlist():
    return _make_allowlist("192.168.1.143")


@pytest.fixture
def client(allowlist):
    """Create a test client with the allowlist injected."""
    import soundcork.main as main_mod

    # Inject our test allowlist into the module global
    original = main_mod._speaker_allowlist
    main_mod._speaker_allowlist = allowlist
    try:
        yield TestClient(main_mod.app)
    finally:
        main_mod._speaker_allowlist = original


class TestBoseProtocolIPRestriction:
    """Bose protocol endpoints should only accept requests from known speaker IPs."""

    def test_marge_endpoint_allowed_from_known_speaker(self, client):
        # The test client uses 'testclient' as the host by default
        # We need to test that the middleware checks the IP
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={"X-Forwarded-For": "192.168.1.143"},
        )
        assert resp.status_code != 403

    def test_marge_endpoint_blocked_from_unknown_ip(self, client):
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={"X-Forwarded-For": "10.99.99.99"},
        )
        assert resp.status_code == 403

    def test_oauth_token_blocked_from_unknown_ip(self, client):
        resp = client.post(
            "/oauth/device/AABBCCDDEEFF/music/musicprovider/15/token/bearer",
            headers={"X-Forwarded-For": "10.99.99.99"},
        )
        assert resp.status_code == 403

    def test_scan_blocked_from_unknown_ip(self, client):
        resp = client.get(
            "/scan",
            headers={"X-Forwarded-For": "10.99.99.99"},
        )
        assert resp.status_code == 403

    def test_webui_not_blocked(self, client):
        """WebUI endpoints should NOT be restricted by speaker IP."""
        resp = client.get(
            "/webui/",
            headers={"X-Forwarded-For": "10.99.99.99"},
        )
        # Should serve the page regardless of source IP
        assert resp.status_code == 200

    def test_mgmt_not_blocked_by_ip(self, client):
        """Mgmt endpoints use their own Basic Auth, not IP restriction."""
        resp = client.get(
            "/mgmt/spotify/accounts",
            headers={"X-Forwarded-For": "10.99.99.99"},
        )
        # Should get 401 (auth required), not 403 (IP blocked)
        assert resp.status_code == 401

    def test_loopback_always_allowed(self, client):
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={"X-Forwarded-For": "127.0.0.1"},
        )
        assert resp.status_code != 403


class TestWebuiSpeakerProxyRestriction:
    """The webui speaker proxy should only allow proxying to registered speaker IPs."""

    def test_speaker_proxy_allowed_for_registered_ip(self, client):
        # This will fail to connect to the speaker (no real speaker), but shouldn't be 403
        resp = client.get("/webui/api/speaker/192.168.1.143/info")
        assert resp.status_code != 403

    def test_speaker_proxy_blocked_for_unregistered_ip(self, client):
        resp = client.get("/webui/api/speaker/10.99.99.99/info")
        assert resp.status_code == 403

    def test_speaker_proxy_blocks_metadata_ip(self, client):
        resp = client.get("/webui/api/speaker/169.254.169.254/latest/meta-data/")
        assert resp.status_code == 403

    def test_speaker_proxy_blocks_loopback(self, client):
        resp = client.get("/webui/api/speaker/127.0.0.1/etc/passwd")
        assert resp.status_code == 403


class TestWebuiImageProxyRestriction:
    """The image proxy should only allow known CDN domains."""

    def test_image_proxy_allows_tunein_cdn(self, client):
        resp = client.get(
            "/webui/api/image",
            params={"url": "https://cdn-profiles.tunein.com/s2398/images/logoq.jpg"},
        )
        # May fail to connect, but shouldn't be 403
        assert resp.status_code != 403

    def test_image_proxy_allows_spotify_cdn(self, client):
        resp = client.get(
            "/webui/api/image",
            params={"url": "https://image-cdn-ak.spotifycdn.com/image/abc123"},
        )
        assert resp.status_code != 403

    def test_image_proxy_allows_scdn(self, client):
        resp = client.get(
            "/webui/api/image",
            params={"url": "https://i.scdn.co/image/abc123"},
        )
        assert resp.status_code != 403

    def test_image_proxy_blocks_arbitrary_url(self, client):
        resp = client.get(
            "/webui/api/image",
            params={"url": "https://evil.com/steal-data"},
        )
        assert resp.status_code == 403

    def test_image_proxy_blocks_internal_ip(self, client):
        resp = client.get(
            "/webui/api/image",
            params={"url": "http://169.254.169.254/latest/meta-data/"},
        )
        assert resp.status_code == 403

    def test_image_proxy_blocks_localhost(self, client):
        resp = client.get(
            "/webui/api/image",
            params={"url": "http://127.0.0.1:8000/mgmt/spotify/token"},
        )
        assert resp.status_code == 403


class TestWebuiMgmtProxyRestriction:
    """The mgmt proxy should only allow specific safe paths."""

    def test_mgmt_proxy_allows_spotify_accounts(self, client):
        resp = client.get("/webui/api/mgmt/spotify/accounts")
        # May get a connection error to the backend, but not 403
        assert resp.status_code != 403

    def test_mgmt_proxy_allows_spotify_entity(self, client):
        resp = client.post(
            "/webui/api/mgmt/spotify/entity",
            json={"uri": "spotify:playlist:abc"},
        )
        assert resp.status_code != 403

    def test_mgmt_proxy_blocks_spotify_token(self, client):
        """The token endpoint must NOT be exposed through the proxy."""
        resp = client.get("/webui/api/mgmt/spotify/token")
        assert resp.status_code == 403

    def test_mgmt_proxy_blocks_arbitrary_path(self, client):
        # Path traversal: FastAPI normalizes ../.. to 404, or our check returns 403
        resp = client.get("/webui/api/mgmt/../../etc/passwd")
        assert resp.status_code in (403, 404)

    def test_mgmt_proxy_blocks_token_path(self, client):
        resp = client.get("/webui/api/mgmt/spotify/token")
        assert resp.status_code == 403

    def test_mgmt_proxy_blocks_unknown_subpath(self, client):
        resp = client.get("/webui/api/mgmt/devices/AABB/events")
        assert resp.status_code == 403
