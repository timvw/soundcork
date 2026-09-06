"""Regression tests for the server-side Spotify ZeroConf primer wiring."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import soundcork.main as main


def test_lifespan_starts_and_stops_enabled_primer(monkeypatch):
    primer = MagicMock()
    monkeypatch.setattr(main, "zeroconf_primer", primer)
    monkeypatch.setattr(main.settings, "mgmt_password", "test-password")
    monkeypatch.setattr(main.settings, "zeroconf_primer_enabled", True)
    monkeypatch.setattr(main, "get_speaker_allowlist", MagicMock())

    async def exercise():
        async with main.lifespan(main.app):
            primer.start_periodic.assert_called_once_with()
            primer.stop_periodic.assert_not_called()

        primer.stop_periodic.assert_called_once_with()

    asyncio.run(exercise())


def test_lifespan_leaves_disabled_primer_stopped(monkeypatch):
    primer = MagicMock()
    monkeypatch.setattr(main, "zeroconf_primer", primer)
    monkeypatch.setattr(main.settings, "mgmt_password", "test-password")
    monkeypatch.setattr(main.settings, "zeroconf_primer_enabled", False)
    monkeypatch.setattr(main, "get_speaker_allowlist", MagicMock())

    async def exercise():
        async with main.lifespan(main.app):
            pass

    asyncio.run(exercise())

    primer.start_periodic.assert_not_called()
    primer.stop_periodic.assert_not_called()


def test_marge_device_request_registers_speaker_after_success(monkeypatch):
    primer = MagicMock()
    monkeypatch.setattr(main, "zeroconf_primer", primer)
    request = SimpleNamespace(url=SimpleNamespace(path="/marge/streaming/account/1234567/device/AABBCCDDEEFF/presets"))
    call_next = AsyncMock(return_value=SimpleNamespace(status_code=200))

    response = asyncio.run(main.register_speakers_middleware(request, call_next))

    assert response.status_code == 200
    primer.register_speaker.assert_called_once_with("1234567", "AABBCCDDEEFF")


def test_marge_device_request_does_not_register_after_failure(monkeypatch):
    primer = MagicMock()
    monkeypatch.setattr(main, "zeroconf_primer", primer)
    request = SimpleNamespace(url=SimpleNamespace(path="/marge/streaming/account/1234567/device/AABBCCDDEEFF/presets"))
    call_next = AsyncMock(return_value=SimpleNamespace(status_code=404))

    asyncio.run(main.register_speakers_middleware(request, call_next))

    primer.register_speaker.assert_not_called()


def test_power_on_notifies_primer_with_speaker_source_ip(monkeypatch):
    primer = MagicMock()
    monkeypatch.setattr(main, "zeroconf_primer", primer)
    monkeypatch.setattr(main, "update_device_poweron", MagicMock(return_value="1234567"))
    request = SimpleNamespace(
        headers={"x-forwarded-for": "192.168.1.42, 10.0.0.1"},
        body=AsyncMock(return_value=b"<info/>"),
    )
    response = main.Response()

    result = asyncio.run(main.power_on(request, response))

    assert result.status_code == 200
    primer.on_power_on.assert_called_once_with("192.168.1.42")
