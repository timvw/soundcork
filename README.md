# SoundCork

Keep your Bose SoundTouch speaker fully functional after Bose shuts down the SoundTouch cloud servers on May 6, 2026.

SoundCork is a self-hosted replacement for the four Bose cloud servers that SoundTouch speakers depend on. It serves all responses locally — no traffic to Bose, no risk of unwanted firmware updates, no data leaving your network.

Fork of [deborahgu/soundcork](https://github.com/deborahgu/soundcork) with added Docker support, smart proxy mode, and deployment guides.

## What Works

| Feature | Status | Notes |
|---------|--------|-------|
| TuneIn radio presets | Working | Presets 1-6, station playback |
| Spotify Connect | Working | Cast from the Spotify app — independent of Bose servers |
| Spotify presets | Working | Requires a [one-time kick-start](docs/spotify.md#fixing-spotify-presets) via Spotify Connect |
| AUX input | Working | Not affected by shutdown |
| Bluetooth | Working | Not affected by shutdown |
| Firmware updates | Blocked | SoundCork returns "no updates available" |
| SoundTouch app presets | Not working | App can no longer configure TuneIn presets — use [Bose CLI](https://github.com/timvw/bose) instead |

## Quick Start

```bash
docker run -d --name soundcork \
  -p 8000:8000 \
  -v ./data:/soundcork/data \
  -e base_url=http://your-server:8000 \
  -e data_dir=/soundcork/data \
  ghcr.io/timvw/soundcork:main
```

Verify it's running:
```bash
curl http://your-server:8000/
# {"Bose":"Can't Brick Us"}
```

The container image supports `linux/amd64` and `linux/arm64` (Raspberry Pi).

See [Deployment Guide](docs/deployment.md) for Docker Compose, Kubernetes, and bare metal options.

## Setup

1. **Get SSH access** to your speaker — [Speaker Setup Guide](docs/speaker-setup.md#step-1-enable-ssh-access)
2. **Extract your speaker data** (presets, sources, device info) — [Speaker Setup Guide](docs/speaker-setup.md#step-2-extract-speaker-data)
3. **Deploy SoundCork** on your network — [Deployment Guide](docs/deployment.md)
4. **Redirect your speaker** to SoundCork — [Speaker Setup Guide](docs/speaker-setup.md#step-3-redirect-speaker-to-soundcork)

## How It Works

SoundTouch speakers communicate with four Bose cloud servers. SoundCork replaces all of them by editing the speaker's configuration to point to your server instead.

See [Architecture](docs/architecture.md) for details on the Bose servers, operating modes, and data flows.

## Bose CLI

The official SoundTouch app can no longer configure presets pointing to TuneIn stations. The [Bose CLI](https://github.com/timvw/bose) talks directly to the speaker's local API (port 8090) and works independently of any cloud server:

```bash
brew install timvw/tap/bose
bose preset    # view presets
bose status    # speaker status
bose volume 30 # set volume
```

## Documentation

- [Speaker Setup Guide](docs/speaker-setup.md) — SSH access, data extraction, speaker redirect
- [Deployment Guide](docs/deployment.md) — Docker, Docker Compose, Kubernetes, bare metal
- [Architecture](docs/architecture.md) — Bose servers, proxy modes, circuit breaker, data flows
- [Spotify Guide](docs/spotify.md) — Spotify Connect vs SoundTouch Spotify, preset fix
- [API Specification](docs/API_Spec.md) — Reverse-engineered Bose server API
- [Shutdown Emulation](docs/Shutdown_Emulation.md) — Test results without Bose servers

## Credits

- [deborahgu](https://github.com/deborahgu) for creating the original [soundcork](https://github.com/deborahgu/soundcork) project
- Bose for publishing the [SoundTouch Web API documentation](https://assets.bosecreative.com/m/496577402d128874/original/SoundTouch-Web-API.pdf) to support community developers

## License

MIT — see [LICENSE](LICENSE)
