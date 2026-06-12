import base64
import json
import urllib.parse

from soundcork.bmx import tunein_navigate_v1, tunein_search_v1


class FakeTuneInResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def encode_uri(uri: str) -> str:
    return base64.urlsafe_b64encode(uri.encode()).decode()


def decode_navigate_href(href: str) -> str:
    return base64.urlsafe_b64decode(href.rsplit("/", 1)[-1]).decode()


def test_navigate_uses_ashx_parser_for_opml_browse_urls(monkeypatch):
    tunein_uri = "http://opml.radiotime.com/Browse.ashx?c=podcast&render=json"
    requested_urls = []

    def fake_urlopen(url):
        requested_urls.append(url)
        return FakeTuneInResponse(
            {
                "head": {"title": "Podcasts"},
                "body": [
                    {
                        "type": "link",
                        "text": "News",
                        "subtext": "Latest episodes",
                        "image": "http://example.com/news.png",
                        "URL": "http://opml.radiotime.com/Browse.ashx?c=news",
                    }
                ],
            }
        )

    monkeypatch.setattr("soundcork.bmx.urllib.request.urlopen", fake_urlopen)

    response = tunein_navigate_v1(encode_uri(tunein_uri))

    assert requested_urls == [tunein_uri]
    assert response.bmx_sections[0].name == "Podcasts"
    assert response.bmx_sections[0].items[0].name == "News"

    navigate_href = response.bmx_sections[0].items[0].links.bmx_navigate.href
    assert decode_navigate_href(navigate_href) == "http://opml.radiotime.com/Browse.ashx?c=news&render=json"


def test_search_url_encodes_spaces_and_more_link_uses_encoded_query(monkeypatch):
    requested_urls = []

    def fake_urlopen(url):
        requested_urls.append(url)
        return FakeTuneInResponse(
            {
                "Items": [
                    {
                        "Type": "Container",
                        "ContainerType": "PlayableStations",
                        "Title": "Stations",
                        "Children": [
                            {
                                "Type": "Station",
                                "GuideId": "s12345",
                                "Title": "Radio Paradise",
                                "Subtitle": "Commercial free",
                                "Image": "http://example.com/radio-paradise.png",
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr("soundcork.bmx.urllib.request.urlopen", fake_urlopen)

    response = tunein_search_v1("radio paradise")

    assert " " not in requested_urls[0]
    requested_query = urllib.parse.parse_qs(urllib.parse.urlsplit(requested_urls[0]).query)
    assert requested_query["query"] == ["radio paradise"]

    section_href = response.bmx_sections[0].links.self.href
    decoded_section_uri = decode_navigate_href(section_href)
    assert " " not in decoded_section_uri
    decoded_query = urllib.parse.parse_qs(urllib.parse.urlsplit(decoded_section_uri).query)
    assert decoded_query["query"] == ["radio paradise"]
    assert response.bmx_sections[0].items[0].links.bmx_playback.href == ("/v1/playback/station/s12345")
