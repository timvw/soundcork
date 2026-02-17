# SoundCork Documentation Design

Date: 2026-02-17

## Goal

Document all work done on soundcork so other Bose SoundTouch owners can keep their speakers alive after the Bose SoundTouch cloud shutdown on May 6, 2026 (extended from the original February 18 date). Three outputs targeting progressive depth: blog post (discovery), README (quick start), detailed docs (deep dive).

## Audience

All levels — from non-technical SoundTouch owners to developers who want to contribute. Content starts accessible and offers technical depth further in.

## Outputs

### 1. README.md (soundcork repo)

Replaces deborahgu's original README (preserved in git history). ~100 lines.

Structure:
- **Header**: SoundCork — Keep Your Bose SoundTouch Speaker Alive
- **What Still Works**: Table of features and status
- **Quick Start**: Docker one-liner with env vars and volume mount
- **What You Need**: Speaker with SSH access, server, speaker data (extracted once)
- **Setup Overview**: 4 numbered steps linking to detailed docs
- **How It Works**: Brief architecture description, link to docs/architecture.md
- **Bose CLI**: Link to github.com/timvw/bose for direct speaker control on port 8090
- **Credits**: deborahgu for the original project
- **License**: Existing MIT license

### 2. Detailed docs/ (soundcork repo)

#### docs/speaker-setup.md
- Prerequisites (speaker model, clean FAT32 USB, Ethernet cable)
- Enable SSH on firmware 27.x (USB stick method)
  - macOS junk file removal (mdutil, .fseventsd, .Spotlight-V100)
  - Note: we changed USB cleanliness AND switched to Ethernet simultaneously; can't isolate which fixed it
- Make SSH persistent (`touch /mnt/nv/remote_services`)
- Finding speaker IP
- Extract speaker data (Presets.xml, Recents.xml, Sources.xml, DeviceInfo.xml)
  - Which come from port 8090 vs SSH
  - Data directory structure for soundcork
- Redirect speaker: edit SoundTouchSdkPrivateCfg.xml
  - Before/after examples for all 4 server URLs
  - `rw` command to make filesystem writable
- Warnings: port 17000 TAP console dangers, `demo enter` factory mode

#### docs/deployment.md
- Option 1: Docker (simplest) — `docker run` one-liner
- Option 2: Docker Compose — full docker-compose.yml
- Option 3: Kubernetes — example manifests (namespace, deployment, service, ingress), note about customizing hostname/volume/ingress type
- Option 4: Bare metal — Python 3.12, venv, gunicorn, systemd (reference original approach)
- Environment variables table (base_url, data_dir, SOUNDCORK_MODE, SOUNDCORK_LOG_DIR)
- Container image details (ghcr.io, multi-arch amd64+arm64, GitHub Actions CI)
- Verification steps

#### docs/architecture.md
- The problem: 4 cloud servers, Bose is shutting them down on May 6, 2026 (extended from Feb 18)
- Reference: https://www.bose.co.uk/en_gb/landing_pages/soundtouch-eol.html
- Note: Bose published official API docs for community developers: https://assets.bosecreative.com/m/496577402d128874/original/SoundTouch-Web-API.pdf
- The four Bose servers: table with name, internal name, purpose, status (as of Feb 2026)
  - streaming.bose.com (marge): ALIVE (servers not shut down until May 6)
  - content.api.bose.io (bmx): API REMOVED (server responds but 404s all endpoints — early deprecation before full shutdown)
  - worldwide.bose.com (updates): API REMOVED (same — 404s)
  - events.api.bosecm.com (stats): telemetry only, safe to ignore
- How SoundCork replaces them: speaker config → soundcork → local handlers
- Local mode vs proxy mode
  - Local (recommended): all responses from local data, zero Bose traffic
  - Proxy: tries upstream first, circuit breaker fallback, useful for initial capture
  - Why local is recommended: marge can serve firmware updates
- Circuit breaker design: per-server health tracking, open on errors/404/5xx, 5-minute cooldown, half-open probe
- Data flow: power-on sequence, TuneIn playback, Spotify (independent)
- Traffic logging (JSONL format, proxy mode only)

#### docs/spotify.md
- Two different Spotify systems (common confusion)
  - Spotify Connect: direct LAN, speaker ↔ Spotify CDN, no Bose involved, always works
  - SoundTouch Spotify integration: through marge, Bose's client ID, broken in SoundTouch app
- Spotify preset fix: kick-start via Spotify Connect
  - Play any song from Spotify app → select speaker → then preset works
  - Why: Spotify Connect authenticates speaker's embedded client via ZeroConf
  - Session lives in speaker RAM, token in Sources.xml doesn't change
  - May need to repeat after reboot
- SoundTouch app can no longer configure TuneIn presets → use Bose CLI
- Traffic analysis evidence (what we observed in logs)

#### docs/API_Spec.md — Keep existing (already comprehensive)
#### docs/Shutdown_Emulation.md — Keep existing

### 3. Example data files (soundcork repo)

Directory: `examples/`

| File | Contents | Sanitized |
|------|----------|-----------|
| examples/Presets.xml | 5 TuneIn + 1 Spotify preset | Spotify account → placeholder |
| examples/Sources.xml | AUX, INTERNET_RADIO, LOCAL_INTERNET_RADIO, SPOTIFY, TUNEIN | All tokens → REDACTED |
| examples/Recents.xml | Mix of TuneIn and Spotify | Device ID, Spotify account → placeholder |
| examples/DeviceInfo.xml | SoundTouch 20 structure | Serials, IPs, MACs, account → placeholder |

Real TuneIn station IDs kept (they're public). Structure shows exactly what soundcork expects.

### 4. Blog post (timvw.be)

File: `content/posts/2026/02/17/keep-your-bose-soundtouch-alive.md`

Hugo frontmatter: title, date, draft: false, tags: [bose, soundtouch, self-hosting, reverse-engineering, docker], categories: [self-hosting]

Structure (~120 lines, tutorial format):
- Opening: Bose is shutting down SoundTouch servers on May 6, 2026 — here's how to keep your speaker fully functional
- What stopped working vs what still works without changes
- The fix: SoundCork (brief intro, credit deborahgu, fork link)
- Step by step: SSH access → extract data → deploy (Docker) → redirect speaker → verify
- Spotify: it's complicated (brief, link to docs/spotify.md)
- Bose CLI for preset management (github.com/timvw/bose)
- Closing: speaker is fully independent, link to repo

### 5. Upstream contributions (deborahgu/soundcork)

#### New issues to open
1. "Add Dockerfile and Docker deployment support"
2. "Add example data files (Presets, Sources, Recents, DeviceInfo)"
3. "Document SSH access on firmware 27.x (USB stick method)"
4. "Document Spotify behavior: Connect vs SoundTouch integration"
5. "Document Bose server status (pre-shutdown, some APIs already returning 404)"
6. "Add Kubernetes deployment example"

#### Existing issues to reference
- Issue #152: "Add proxy functionality" — our proxy.py addresses this directly
- Issue #159: "Investigate automatic token setup" — comment with Spotify Connect findings

#### PRs to open (after issues are created)
1. Dockerfile + .dockerignore + Docker deployment docs
2. Proxy middleware (proxy.py, config.py changes, httpx dep) → references #152
3. Example data files
4. Documentation (speaker-setup, spotify, architecture, server status)
5. Kubernetes example manifests

## Design Decisions

- **README replaces original**: Fork is the user's own repo now. Original preserved in git history. Credit given prominently.
- **Local mode as default recommendation**: Marge is still alive and could push firmware updates. Local mode = zero Bose dependency.
- **Honest documentation of unknowns**: USB+Ethernet change documented as two simultaneous changes. Spotify token behavior documented with traffic evidence.
- **Example files with real TuneIn stations**: Station IDs are public (s102123 = Joe, s69243 = QMusic, etc.). Only credentials/account IDs redacted.
- **Blog post is tutorial, not story**: Practical focus — readers want to fix their speaker, not read about our journey. Links to repo for depth.
- **Correct shutdown date**: May 6, 2026 (extended from Feb 18). Servers partly alive but BMX already returning 404s. Bose published official API docs for community developers.
- **Reference Bose's official API docs**: Bose explicitly supports community tools — link to their published SoundTouch-Web-API.pdf.
