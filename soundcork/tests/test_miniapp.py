from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from soundcork.miniapp import get_miniapp_router
from soundcork.model import Preset

ACCOUNT_ID = "8208423"
DEVICE_ID = "device-1"


class FakeDatastore:
    def account_exists(self, account_id: str) -> bool:
        return account_id == ACCOUNT_ID

    def list_accounts(self) -> list[str]:
        return [ACCOUNT_ID]

    def get_account_info(self, account_id: str) -> str:
        assert account_id == ACCOUNT_ID
        return "Účet ložnice"

    def list_devices(self, account_id: str) -> list[str]:
        assert account_id == ACCOUNT_ID
        return [DEVICE_ID]

    def get_device_info(self, account_id: str, device_id: str):
        assert account_id == ACCOUNT_ID
        assert device_id == DEVICE_ID
        return SimpleNamespace(
            name="ložnice",
            product_code="SoundTouch10",
            device_id=DEVICE_ID,
        )

    def get_presets(self, account_id: str) -> list[Preset]:
        assert account_id == ACCOUNT_ID
        return [
            Preset(
                id="4",
                name="Rádio Proglas",
                source="LOCAL_INTERNET_RADIO",
                type="STORED_MUSIC",
                location="proglas",
                container_art="",
            )
        ]


class FakeSpeakers:
    # Codex: Keep this fake complete enough to exercise dashboard rendering.
    def __init__(self, play_result: bool = True, online: bool = True) -> None:
        self.play_result = play_result
        self.online = online
        self.play_calls: list[tuple[str, str]] = []

    def all_devices(self):
        return {
            DEVICE_ID: SimpleNamespace(
                account=ACCOUNT_ID,
                online=self.online,
                in_soundcork=True,
                marge_server="Soundcork",
            )
        }

    def play_content_item(self, device_id: str, content_item_id: str) -> bool:
        self.play_calls.append((device_id, content_item_id))
        return self.play_result

    def get_now_playing_status(self, device_id: str):
        assert device_id == DEVICE_ID
        return SimpleNamespace(
            StationName="Rádio Proglas",
            ContentItem=SimpleNamespace(Name="Rádio Proglas"),
            ContainerArtUrl="/art.png",
            PlayStatus="PLAY_STATE",
        )

    def get_volume(self, device_id: str):
        assert device_id == DEVICE_ID
        return SimpleNamespace(Actual=25, Target=25, IsMuted=False)


def make_client(monkeypatch, speakers: FakeSpeakers | None = None):
    monkeypatch.chdir(Path(__file__).resolve().parents[1])
    app = FastAPI()
    fake_speakers = speakers or FakeSpeakers()
    app.include_router(get_miniapp_router(cast(Any, FakeDatastore()), cast(Any, fake_speakers)))
    return TestClient(app), fake_speakers


def set_cookie_headers(response) -> list[str]:
    return response.headers.get_list("set-cookie")


def test_dashboard_decodes_display_cookies(monkeypatch):
    client, _speakers = make_client(monkeypatch)

    response = client.get(
        "/miniapp/dashboard",
        headers={
            "Cookie": (f"soundcork_account_id={ACCOUNT_ID}; soundcork_account_label=%C3%9A%C4%8Det%20lo%C5%BEnice; ")
        },
    )

    assert response.status_code == 200
    assert "Účet ložnice" in response.text
    assert f'data-account-id="{ACCOUNT_ID}"' in response.text
    assert f'id="{DEVICE_ID}-info"' in response.text
    assert "code.jquery.com" not in response.text


def test_dashboard_disables_offline_device(monkeypatch):
    client, _speakers = make_client(monkeypatch, FakeSpeakers(online=False))

    response = client.get(
        "/miniapp/dashboard",
        headers={"Cookie": f"soundcork_account_id={ACCOUNT_ID}"},
    )

    assert response.status_code == 200
    assert 'disabled aria-disabled="true"' in response.text


def test_account_cookie_is_http_only(monkeypatch):
    client, _speakers = make_client(monkeypatch)

    response = client.post(
        "/miniapp/login",
        data={"account_id": ACCOUNT_ID},
        follow_redirects=False,
    )

    account_cookie = next(
        header for header in set_cookie_headers(response) if header.startswith("soundcork_account_id=")
    )
    assert "HttpOnly" in account_cookie


def test_websocket_client_has_offline_safe_lifecycle():
    # Codex: Static contract for the dependency-free browser module.
    js = (Path(__file__).resolve().parents[1] / "static/js/soundtouch_websocket.js").read_text()
    handler = (Path(__file__).resolve().parents[1] / "static/js/miniapp_handler.js").read_text()

    assert "cookieStore" not in handler
    assert "document.body.dataset.accountId" in handler
    assert "setTimeout" in js
    assert 'addEventListener("close"' in js
    assert "textContent" in js
    assert "$." not in js
