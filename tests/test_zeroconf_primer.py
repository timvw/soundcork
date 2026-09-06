"""Unit tests for Spotify ZeroConf primer lifecycle and token caching."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import soundcork.zeroconf_primer as primer_module
from soundcork.zeroconf_primer import ZeroConfPrimer


def _primer(tmp_path):
    spotify = MagicMock()
    datastore = MagicMock()
    datastore.list_accounts.return_value = []
    settings = SimpleNamespace(
        data_dir=str(tmp_path),
        spotify_client_id="client-id",
    )
    return ZeroConfPrimer(spotify, datastore, settings), spotify, datastore


def test_stop_during_periodic_tick_does_not_rearm_timer(monkeypatch, tmp_path):
    timers = []

    class FakeTimer:
        def __init__(self, interval, function):
            self.interval = interval
            self.function = function
            self.daemon = False
            self.cancelled = False
            timers.append(self)

        def start(self):
            pass

        def cancel(self):
            self.cancelled = True

    monkeypatch.setattr(primer_module.threading, "Timer", FakeTimer)
    primer, _, _ = _primer(tmp_path)

    primer.start_periodic()
    primer.stop_periodic()
    primer._periodic_tick()

    assert len(timers) == 1
    assert timers[0].cancelled is True


def test_power_on_discovers_speakers_when_registry_is_empty(monkeypatch, tmp_path):
    primer, _, _ = _primer(tmp_path)
    speaker = SimpleNamespace(ip_address="192.168.1.42")

    def seed():
        primer._speakers["AABBCCDDEEFF"] = speaker

    monkeypatch.setattr(primer, "_seed_from_datastore", MagicMock(side_effect=seed))
    monkeypatch.setattr(primer_module, "BOOT_RETRY_DELAYS", [0])
    monkeypatch.setattr(primer_module.time, "sleep", MagicMock())
    monkeypatch.setattr(primer, "_prime_if_needed", MagicMock(return_value=True))

    primer._power_on_prime()

    primer._seed_from_datastore.assert_called_once_with()
    primer._prime_if_needed.assert_called_once_with(speaker)


def test_token_cache_uses_actual_spotify_expiration(monkeypatch, tmp_path):
    primer, spotify, _ = _primer(tmp_path)
    spotify.get_spotify_user_id.return_value = "spotify-user"
    spotify.get_fresh_token_with_expiry_sync.return_value = ("access-token", 1_100)
    monkeypatch.setattr(primer_module.time, "time", MagicMock(return_value=1_000))

    assert primer._get_token() == ("access-token", "spotify-user")
    assert primer._token_expires_at == 1_100


def test_seed_uses_datastore_account_listing(tmp_path):
    primer, _, datastore = _primer(tmp_path)
    datastore.list_accounts.return_value = ["1234567"]
    datastore.list_devices.return_value = []

    primer._seed_from_datastore()

    datastore.list_accounts.assert_called_once_with()
    datastore.list_devices.assert_called_once_with("1234567")
