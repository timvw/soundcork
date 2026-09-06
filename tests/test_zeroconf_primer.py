"""Unit tests for Spotify ZeroConf primer lifecycle and token caching."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import soundcork.zeroconf_primer as primer_module
from soundcork.marge import update_device_poweron
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


def test_periodic_check_reprimes_stale_active_speaker(monkeypatch, tmp_path):
    primer, _, _ = _primer(tmp_path)
    speaker = primer_module.TrackedSpeaker(
        account_id="1234567",
        device_id="AABBCCDDEEFF",
        ip_address="192.168.1.42",
        last_primed=100,
    )
    monkeypatch.setattr(primer_module.time, "time", MagicMock(return_value=100 + primer_module.PERIODIC_CHECK_SECONDS))
    monkeypatch.setattr(primer, "_get_active_user", MagicMock(return_value="spotify-user"))
    monkeypatch.setattr(primer, "_prime_speaker", MagicMock(return_value=True))

    assert primer._prime_if_needed(speaker) is True
    primer._prime_speaker.assert_called_once_with(speaker)


def test_active_speaker_resets_consecutive_failures(monkeypatch, tmp_path):
    primer, _, _ = _primer(tmp_path)
    speaker = primer_module.TrackedSpeaker(
        account_id="1234567",
        device_id="AABBCCDDEEFF",
        ip_address="192.168.1.42",
        last_primed=900,
        prime_failures=4,
    )
    monkeypatch.setattr(primer_module.time, "time", MagicMock(return_value=1_000))
    monkeypatch.setattr(primer, "_get_active_user", MagicMock(return_value="spotify-user"))
    monkeypatch.setattr(primer, "_prime_speaker", MagicMock(return_value=True))

    assert primer._prime_if_needed(speaker) is True
    assert speaker.prime_failures == 0
    primer._prime_speaker.assert_not_called()


def test_registration_retries_ip_resolution(monkeypatch, tmp_path):
    primer, _, _ = _primer(tmp_path)
    monkeypatch.setattr(primer, "_resolve_speaker_ip", MagicMock(side_effect=[None, "192.168.1.42"]))
    threads = []

    class FakeThread:
        def __init__(self, **kwargs):
            threads.append(kwargs)

        def start(self):
            pass

    monkeypatch.setattr(primer_module.threading, "Thread", FakeThread)

    primer.register_speaker("1234567", "AABBCCDDEEFF")
    primer.register_speaker("1234567", "AABBCCDDEEFF")

    assert primer._resolve_speaker_ip.call_count == 2
    assert primer._speakers["AABBCCDDEEFF"].ip_address == "192.168.1.42"
    assert len(threads) == 1


def test_power_on_requests_are_coalesced(monkeypatch, tmp_path):
    primer, _, _ = _primer(tmp_path)
    threads = []

    class FakeThread:
        def __init__(self, **kwargs):
            threads.append(kwargs)

        def start(self):
            pass

    monkeypatch.setattr(primer_module.threading, "Thread", FakeThread)

    primer.on_power_on()
    primer.on_power_on()

    assert len(threads) == 1


def test_resolve_speaker_ip_rejects_non_private_target(tmp_path):
    primer, _, datastore = _primer(tmp_path)
    datastore.get_device_info.return_value.ip_address = "attacker.example"
    assert primer._resolve_speaker_ip("1234567", "AABBCCDDEEFF") is None

    datastore.get_device_info.return_value.ip_address = "8.8.8.8"
    assert primer._resolve_speaker_ip("1234567", "AABBCCDDEEFF") is None

    datastore.get_device_info.return_value.ip_address = "192.168.1.42"
    assert primer._resolve_speaker_ip("1234567", "AABBCCDDEEFF") == "192.168.1.42"


def test_power_on_persists_observed_ip_instead_of_untrusted_xml():
    datastore = MagicMock()
    reported = SimpleNamespace(device_id="AABBCCDDEEFF", ip_address="192.168.1.66")
    current = SimpleNamespace(device_id="AABBCCDDEEFF", ip_address="192.168.1.42")
    datastore.device_info_from_poweron_xml.return_value = reported
    datastore.find_device.return_value = current, "1234567"

    account = update_device_poweron(datastore, b"<info/>", "192.168.1.43")

    assert account == "1234567"
    assert current.ip_address == "192.168.1.43"
    datastore.save_device_info.assert_called_once_with(current, "1234567")
