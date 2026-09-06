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
        created_on="2026-01-01T00:00:00",
        updated_on="2026-01-01T00:00:00",
    )


def _make_allowlist(*ips: str) -> SpeakerAllowlist:
    ds = MagicMock()
    ds.list_accounts.return_value = [f"acct{i}" for i in range(len(ips))]
    ds.list_devices.side_effect = [[f"DEV{i:010d}00"] for i in range(len(ips))]
    ds.get_device_info.side_effect = [_make_device_info(ip, f"DEV{i:010d}00") for i, ip in enumerate(ips)]
    return SpeakerAllowlist(ds)


@pytest.fixture
def allowlist():
    return _make_allowlist("192.168.1.143")


@pytest.fixture
def client(allowlist):
    """Create a test client with the allowlist injected."""
    import soundcork.main as main_mod

    # Inject our test allowlist into the module global
    original_allowlist = main_mod._speaker_allowlist
    original_trusted_proxy_ips = main_mod.settings.trusted_proxy_ips
    main_mod._speaker_allowlist = allowlist
    main_mod.settings.trusted_proxy_ips = "testclient"
    try:
        yield TestClient(main_mod.app)
    finally:
        main_mod._speaker_allowlist = original_allowlist
        main_mod.settings.trusted_proxy_ips = original_trusted_proxy_ips


def _login(client) -> str:
    """Login to webui and return CSRF token. Modifies client cookies in-place."""
    with patch("soundcork.webui.auth.Settings") as MockSettings:
        MockSettings.return_value.mgmt_username = "admin"
        MockSettings.return_value.mgmt_password = "secret"
        resp = client.post(
            "/webui/api/login",
            json={"username": "admin", "password": "secret"},
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        return resp.json()["csrf_token"]


@pytest.fixture
def authed_client(client):
    """Test client with an active webui session."""
    csrf = _login(client)
    client._csrf_token = csrf
    return client


class TestBoseProtocolIPRestriction:
    """Bose protocol endpoints should only accept requests from known speaker IPs."""

    def test_marge_endpoint_allowed_from_known_speaker(self, client):
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={"X-Forwarded-For": "192.168.1.143"},
        )
        assert resp.status_code != 403

    def test_marge_endpoint_blocked_from_unknown_ip(self, client):
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={"X-Forwarded-For": "203.0.113.99"},
        )
        assert resp.status_code == 403

    def test_oauth_token_blocked_from_unknown_ip(self, client):
        resp = client.post(
            "/oauth/device/AABBCCDDEEFF/music/musicprovider/15/token/bearer",
            headers={"X-Forwarded-For": "203.0.113.99"},
        )
        assert resp.status_code == 403

    def test_scan_blocked_from_unknown_ip(self, client):
        resp = client.get(
            "/scan",
            headers={"X-Forwarded-For": "203.0.113.99"},
        )
        assert resp.status_code == 403

    def test_webui_not_blocked_by_ip(self, client):
        """WebUI endpoints should NOT be restricted by speaker IP."""
        resp = client.get(
            "/webui/",
            headers={"X-Forwarded-For": "203.0.113.99"},
            follow_redirects=False,
        )
        assert resp.status_code != 403

    def test_mgmt_not_blocked_by_ip(self, client):
        """Mgmt endpoints use their own Basic Auth, not IP restriction."""
        resp = client.get(
            "/mgmt/spotify/accounts",
            headers={"X-Forwarded-For": "203.0.113.99"},
        )
        assert resp.status_code == 401

    def test_loopback_always_allowed(self, client):
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={"X-Forwarded-For": "127.0.0.1"},
        )
        assert resp.status_code != 403

    def test_xff_all_unknown_public_ips_blocked(self, client):
        """When every XFF entry is an unknown public IP, the request is blocked."""
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={"X-Forwarded-For": "203.0.113.1, 203.0.113.99"},
        )
        assert resp.status_code == 403

    def test_xff_spoofing_real_ip_last_allowed(self, client):
        """When the real IP (last entry) is a known speaker, allow it."""
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={"X-Forwarded-For": "203.0.113.99, 192.168.1.143"},
        )
        assert resp.status_code != 403

    def test_xff_spoofing_private_ip_first_is_blocked(self, client):
        """Spoofed private IP entries must not bypass checks."""
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={"X-Forwarded-For": "192.168.1.50, 203.0.113.99"},
        )
        assert resp.status_code == 403

    def test_xff_invalid_rightmost_entry_fails_closed(self, client):
        """An invalid value appended by a trusted proxy must not expose client XFF."""
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={"X-Forwarded-For": "192.168.1.143, unknown"},
        )
        assert resp.status_code == 403

    def test_cf_connecting_ip_ignored(self, client):
        """CF-Connecting-IP should not override XFF-derived client identity."""
        resp = client.get(
            "/marge/streaming/sourceproviders",
            headers={
                "X-Forwarded-For": "203.0.113.99",
                "CF-Connecting-IP": "192.168.1.143",
            },
        )
        assert resp.status_code == 403

    def test_forwarded_headers_ignored_for_untrusted_proxy(self, client):
        """Forwarding headers are ignored when the direct peer is untrusted."""
        import soundcork.main as main_mod

        original_trusted_proxy_ips = main_mod.settings.trusted_proxy_ips
        main_mod.settings.trusted_proxy_ips = ""
        try:
            resp = client.get(
                "/marge/streaming/sourceproviders",
                headers={"X-Forwarded-For": "192.168.1.143"},
            )
        finally:
            main_mod.settings.trusted_proxy_ips = original_trusted_proxy_ips
        assert resp.status_code == 403


class TestWebuiSpeakerProxyRestriction:
    """The webui speaker proxy should only allow proxying to registered speaker IPs."""

    def test_speaker_proxy_allowed_for_registered_ip(self, authed_client):
        resp = authed_client.get("/webui/api/speaker/192.168.1.143/info")
        assert resp.status_code != 403

    def test_speaker_proxy_blocked_for_unregistered_ip(self, authed_client):
        resp = authed_client.get("/webui/api/speaker/203.0.113.99/info")
        assert resp.status_code == 403

    def test_speaker_proxy_blocks_metadata_ip(self, authed_client):
        resp = authed_client.get("/webui/api/speaker/169.254.169.254/latest/meta-data/")
        assert resp.status_code == 403

    def test_speaker_proxy_blocks_loopback(self, authed_client):
        resp = authed_client.get("/webui/api/speaker/127.0.0.1/etc/passwd")
        assert resp.status_code == 403


class TestWebuiImageProxyRestriction:
    """The image proxy should only allow known CDN domains."""

    def test_image_proxy_allows_tunein_cdn(self, authed_client):
        resp = authed_client.get(
            "/webui/api/image",
            params={"url": "https://cdn-profiles.tunein.com/s2398/images/logoq.jpg"},
        )
        assert resp.status_code != 403

    def test_image_proxy_allows_spotify_cdn(self, authed_client):
        resp = authed_client.get(
            "/webui/api/image",
            params={"url": "https://image-cdn-ak.spotifycdn.com/image/abc123"},
        )
        assert resp.status_code != 403

    def test_image_proxy_allows_scdn(self, authed_client):
        resp = authed_client.get(
            "/webui/api/image",
            params={"url": "https://i.scdn.co/image/abc123"},
        )
        assert resp.status_code != 403

    def test_image_proxy_blocks_arbitrary_url(self, authed_client):
        resp = authed_client.get(
            "/webui/api/image",
            params={"url": "https://evil.com/steal-data"},
        )
        assert resp.status_code == 403

    def test_image_proxy_blocks_extension_bypass(self, authed_client):
        resp = authed_client.get(
            "/webui/api/image",
            params={"url": "https://evil.com/logo.png"},
        )
        assert resp.status_code == 403

    def test_image_proxy_blocks_internal_ip(self, authed_client):
        resp = authed_client.get(
            "/webui/api/image",
            params={"url": "http://169.254.169.254/latest/meta-data/"},
        )
        assert resp.status_code == 403

    def test_image_proxy_blocks_localhost(self, authed_client):
        resp = authed_client.get(
            "/webui/api/image",
            params={"url": "http://127.0.0.1:8000/mgmt/spotify/token"},
        )
        assert resp.status_code == 403


class TestWebuiMgmtProxyRestriction:
    """The mgmt proxy should only allow specific safe paths."""

    def test_mgmt_proxy_allows_spotify_accounts(self, authed_client):
        resp = authed_client.get("/webui/api/mgmt/spotify/accounts")
        assert resp.status_code != 403

    def test_mgmt_proxy_allows_spotify_entity(self, authed_client):
        csrf = authed_client._csrf_token
        resp = authed_client.post(
            "/webui/api/mgmt/spotify/entity",
            json={"uri": "spotify:playlist:abc"},
            headers={"X-CSRF-Token": csrf},
        )
        assert resp.status_code != 403

    def test_mgmt_proxy_blocks_spotify_token(self, authed_client):
        """The token endpoint must NOT be exposed through the proxy."""
        resp = authed_client.get("/webui/api/mgmt/spotify/token")
        assert resp.status_code == 403

    def test_mgmt_proxy_blocks_arbitrary_path(self, authed_client):
        resp = authed_client.get("/webui/api/mgmt/../../etc/passwd")
        assert resp.status_code in (403, 404)

    def test_mgmt_proxy_blocks_token_path(self, authed_client):
        resp = authed_client.get("/webui/api/mgmt/spotify/token")
        assert resp.status_code == 403

    def test_mgmt_proxy_blocks_unknown_subpath(self, authed_client):
        resp = authed_client.get("/webui/api/mgmt/devices/AABB/events")
        assert resp.status_code == 403
