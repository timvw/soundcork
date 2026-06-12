"""Tests for RadioBrowser security helpers."""

from unittest.mock import patch

from soundcork.bmx import _is_safe_stream_url, _is_valid_station_id


def _mock_getaddrinfo_public(*args, **kwargs):
    """Simulate DNS resolving to a public IP."""
    return [(2, 1, 6, "", ("93.184.215.14", 0))]


def _mock_getaddrinfo_private(*args, **kwargs):
    """Simulate DNS resolving to a private IP."""
    return [(2, 1, 6, "", ("192.168.1.1", 0))]


def _mock_getaddrinfo_loopback(*args, **kwargs):
    """Simulate DNS resolving to loopback."""
    return [(2, 1, 6, "", ("127.0.0.1", 0))]


def _mock_getaddrinfo_link_local(*args, **kwargs):
    """Simulate DNS resolving to link-local (cloud metadata)."""
    return [(2, 1, 6, "", ("169.254.169.254", 0))]


class TestIsSafeStreamUrl:
    @patch("soundcork.bmx.socket.getaddrinfo", _mock_getaddrinfo_public)
    def test_allows_public_http_url(self):
        assert _is_safe_stream_url("http://stream.example.com:8000/radio.mp3") is True

    @patch("soundcork.bmx.socket.getaddrinfo", _mock_getaddrinfo_public)
    def test_allows_public_https_url(self):
        assert _is_safe_stream_url("https://stream.example.com/live") is True

    @patch("soundcork.bmx.socket.getaddrinfo", _mock_getaddrinfo_loopback)
    def test_blocks_loopback(self):
        assert _is_safe_stream_url("http://evil.com/secret") is False

    @patch("soundcork.bmx.socket.getaddrinfo", _mock_getaddrinfo_private)
    def test_blocks_private_ip(self):
        assert _is_safe_stream_url("http://evil.com/stream") is False

    @patch("soundcork.bmx.socket.getaddrinfo", _mock_getaddrinfo_link_local)
    def test_blocks_link_local(self):
        assert _is_safe_stream_url("http://evil.com/latest/meta-data/") is False

    def test_blocks_file_scheme(self):
        assert _is_safe_stream_url("file:///etc/passwd") is False

    def test_blocks_ftp_scheme(self):
        assert _is_safe_stream_url("ftp://evil.com/payload") is False

    def test_blocks_empty_url(self):
        assert _is_safe_stream_url("") is False

    def test_blocks_no_hostname(self):
        assert _is_safe_stream_url("http:///path") is False


class TestIsValidStationId:
    def test_valid_uuid(self):
        assert _is_valid_station_id("96062a7b-0601-11e8-ae97-52543be04c81") is True

    def test_valid_uuid_uppercase(self):
        assert _is_valid_station_id("96062A7B-0601-11E8-AE97-52543BE04C81") is True

    def test_rejects_empty(self):
        assert _is_valid_station_id("") is False

    def test_rejects_short_string(self):
        assert _is_valid_station_id("not-a-uuid") is False

    def test_rejects_path_traversal(self):
        assert _is_valid_station_id("../../etc/passwd") is False

    def test_rejects_tunein_id(self):
        assert _is_valid_station_id("s12345") is False
