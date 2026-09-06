from types import SimpleNamespace

import soundcork.ui.speakers as speakers_module
from soundcork.ui.speakers import Speakers


# Codex: Verify speaker HTTP calls honor the miniapp's finite timeout budget.
def test_get_now_playing_and_volume_disables_retries(monkeypatch):
    captured: dict[str, object] = {}
    manager = object()

    def fake_pool_manager(**kwargs):
        captured.update(kwargs)
        return manager

    class FakeClient:
        def __init__(self, device, manager):
            assert device == "speaker-device"
            assert manager is not None

        def GetNowPlayingStatus(self):
            return "now-playing"

        def GetVolume(self):
            return "volume"

    speakers = object.__new__(Speakers)
    speakers.all_devices = lambda: {"speaker": SimpleNamespace(st_device="speaker-device")}
    monkeypatch.setattr(speakers_module, "PoolManager", fake_pool_manager)
    monkeypatch.setattr(speakers_module, "SoundTouchClient", FakeClient)

    result = speakers.get_now_playing_and_volume("speaker", timeout=3)

    assert result == ("now-playing", "volume")
    assert captured["retries"] is False
    assert captured["block"] is False
    assert captured["timeout"].total == 1.5
