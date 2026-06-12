## RadioBrowser

[radio-browser.info](https://www.radio-browser.info) is a community-driven internet radio station database with thousands of stations worldwide.

SoundCork integrates RadioBrowser as a first-class source — search, browse, and save stations as presets directly from the Web UI.

### Using the Web UI (recommended)

1. Open the Web UI at `/webui/`
2. Navigate to a speaker, then tap a preset slot
3. Click **"Set RadioBrowser Preset"** (empty slot) or **"Edit (RadioBrowser)"** (filled slot)
4. Search for a station by name (e.g. "Studio Brussel", "BBC Radio 4")
5. Click a result to see station details (country, codec, bitrate, tags)
6. Click **"Set Preset"** to save it

The station is saved as a `RADIO_BROWSER` preset and plays immediately when the preset button is pressed on the speaker.

### Configuration

| Environment variable | Default | Description |
|---------------------|---------|-------------|
| `RADIOBROWSER_API_URL` | `https://de1.api.radio-browser.info` | API mirror to use (override if `de1` is down) |
| `RADIOBROWSER_SSL_DOWNGRADE` | `false` | Downgrade HTTPS stream URLs to HTTP for older speakers that can't verify modern TLS certificates |

### Server-side transcoding

Some RadioBrowser stations use codecs (e.g. HLS, AAC+) that older SoundTouch speakers can't decode. SoundCork can transcode these streams to MP3 via ffmpeg:

- The transcode endpoint is at `/bmx/radiobrowser/v1/transcode/{station_id}`
- Requires `ffmpeg` installed in the container (included in the default Docker image)

### How it works

SoundCork uses source type `RADIO_BROWSER` with the station UUID as location:

```xml
<ContentItem
        source="RADIO_BROWSER"
        type="stationurl"
        isPresetable="true"
        location="/stations/byuuid/9610c454-0601-11e8-ae97-52543be04c81">
    <itemName>RADIO_BROWSER</itemName>
    <containerArt></containerArt>
</ContentItem>
```

The `RADIO_BROWSER` source must be registered in your speaker's `Sources.xml`:
```xml
<source>
    <sourceKey type="RADIO_BROWSER" account="" />
</source>
```

### Manual playback (curl)

```bash
curl -d '<ContentItem source="RADIO_BROWSER" type="stationurl" location="/stations/byuuid/<uuid>"/>' <soundtouch>:8090/select
```

### Security

Stream URLs returned by RadioBrowser are validated via DNS resolution — URLs pointing at private, loopback, link-local, or reserved IP ranges are rejected (SSRF protection). The image proxy for station favicons uses a bounded dynamic allowlist with per-hop redirect validation.
