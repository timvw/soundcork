# SoundCork Documentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Write comprehensive documentation for soundcork across three outputs (README, docs/, blog post), create sanitized example data files, and open upstream issues/PRs on deborahgu/soundcork.

**Architecture:** Layered depth — README for quick start, docs/ for deep dives, blog post for discovery. Example files show exact XML structure. Upstream contributions via GitHub issues then PRs.

**Tech Stack:** Markdown, Hugo (blog), GitHub CLI (gh), XML

**Design doc:** `.opencode/plans/2026-02-17-documentation-design.md`

---

### Task 1: Create Example Data Files

**Files:**
- Create: `examples/Presets.xml`
- Create: `examples/Sources.xml`
- Create: `examples/Recents.xml`
- Create: `examples/DeviceInfo.xml`

**Step 1: Create examples/Presets.xml**

Sanitized version of real presets. Keep TuneIn station IDs (public). Replace Spotify account with placeholder.

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<presets>
  <preset id="1" createdOn="1641383235" updatedOn="1641383235">
    <ContentItem source="TUNEIN" type="stationurl" location="/v1/playback/station/s102123" sourceAccount="" isPresetable="true">
      <itemName>Joe</itemName>
      <containerArt>http://cdn-profiles.tunein.com/s25741/images/logoq.png</containerArt>
    </ContentItem>
  </preset>
  <preset id="2" createdOn="1767861969" updatedOn="1767861969">
    <ContentItem source="TUNEIN" type="stationurl" location="/v1/playback/station/s69243" sourceAccount="" isPresetable="true">
      <itemName>QMusic Belgium</itemName>
      <containerArt />
    </ContentItem>
  </preset>
  <!-- presets 3-5: more TuneIn stations -->
  <preset id="6" createdOn="1547368969" updatedOn="1674297426">
    <ContentItem source="SPOTIFY" type="tracklisturl" location="/playback/container/BASE64_ENCODED_SPOTIFY_URI" sourceAccount="YOUR_SPOTIFY_ACCOUNT_ID" isPresetable="true">
      <itemName>Your Artist Name</itemName>
      <containerArt>https://i.scdn.co/image/ALBUM_ART_HASH</containerArt>
    </ContentItem>
  </preset>
</presets>
```

**Step 2: Create examples/Sources.xml**

All tokens replaced with REDACTED.

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<sources>
    <source displayName="AUX IN" secret="" secretType="">
        <sourceKey type="AUX" account="AUX" />
    </source>
    <source secret="" secretType="token">
        <sourceKey type="INTERNET_RADIO" account="" />
    </source>
    <source secret="REDACTED_BASE64_TOKEN" secretType="token">
        <sourceKey type="LOCAL_INTERNET_RADIO" account="" />
    </source>
    <source displayName="your@email.com" secret="REDACTED_SPOTIFY_OAUTH_TOKEN" secretType="token_version_3">
        <sourceKey type="SPOTIFY" account="YOUR_SPOTIFY_ACCOUNT_ID" />
    </source>
    <source secret="REDACTED_BASE64_TOKEN" secretType="token">
        <sourceKey type="TUNEIN" account="" />
    </source>
</sources>
```

**Step 3: Create examples/Recents.xml**

Device IDs and Spotify accounts replaced.

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<recents>
  <recent deviceID="YOUR_DEVICE_ID" utcTime="1771287920" id="2454152503">
    <contentItem source="SPOTIFY" type="tracklisturl" location="/playback/container/BASE64_ENCODED_URI" sourceAccount="YOUR_SPOTIFY_ACCOUNT_ID" isPresetable="true">
      <itemName>Artist Name</itemName>
    </contentItem>
  </recent>
  <recent deviceID="YOUR_DEVICE_ID" utcTime="1771286998" id="2307122547">
    <contentItem source="TUNEIN" type="stationurl" location="/v1/playback/station/s69243" sourceAccount="" isPresetable="true">
      <itemName>QMusic Belgium</itemName>
    </contentItem>
  </recent>
</recents>
```

**Step 4: Create examples/DeviceInfo.xml**

All identifying info replaced.

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<info deviceID="YOUR_DEVICE_ID">
  <name>Your-Speaker-Name</name>
  <type>SoundTouch 20</type>
  <margeAccountUUID>YOUR_ACCOUNT_ID</margeAccountUUID>
  <components>
    <component>
      <componentCategory>SCM</componentCategory>
      <softwareVersion>27.0.6.46330.5043500 epdbuild.trunk.hepdswbld04.2022-08-04T11:20:29</softwareVersion>
      <serialNumber>XXXXXXXXXXX</serialNumber>
    </component>
    <component>
      <componentCategory>PackagedProduct</componentCategory>
      <serialNumber>XXXXXXXXXXX</serialNumber>
    </component>
  </components>
  <margeURL>https://your-soundcork-server/marge</margeURL>
  <networkInfo type="SCM">
    <macAddress>000000000000</macAddress>
    <ipAddress>192.168.1.x</ipAddress>
  </networkInfo>
  <moduleType>scm</moduleType>
  <variant>spotty</variant>
  <countryCode>EU</countryCode>
</info>
```

**Step 5: Commit**

```bash
git add examples/
git commit -m "docs: add sanitized example data files (Presets, Sources, Recents, DeviceInfo)"
```

---

### Task 2: Write docs/speaker-setup.md

**Files:**
- Create: `docs/speaker-setup.md`

**Step 1: Write the full speaker setup guide**

Content per design doc section on speaker-setup.md:
- Prerequisites: SoundTouch speaker (tested on ST20, fw 27.0.6), clean FAT32 USB, computer on same network, Ethernet cable recommended
- Step 1: Enable SSH (firmware 27.x USB method)
  - Format USB as FAT32
  - Create empty `remote_services` file
  - Remove macOS junk: `mdutil -i off /Volumes/USBNAME`, delete `.fseventsd/`, `.Spotlight-V100/`, `._*` files
  - Note: we changed USB cleanliness AND WiFi→Ethernet simultaneously; if WiFi doesn't work, try Ethernet
  - Power off speaker, insert USB, power on, wait 60s
  - `ssh root@<speaker-ip>` (no password)
- Make persistent: `touch /mnt/nv/remote_services`
- Finding speaker IP: router DHCP, or `bose status` from github.com/timvw/bose
- Step 2: Extract data
  - From speaker port 8090: `curl http://<ip>:8090/presets` → Presets.xml, `curl http://<ip>:8090/recents` → Recents.xml, `curl http://<ip>:8090/info` → DeviceInfo.xml
  - From SSH: `cat /mnt/nv/BoseApp-Persistence/1/Sources.xml` → Sources.xml
  - Account UUID from: `cat /opt/Bose/etc/SoundTouchSdkPrivateCfg.xml` or DeviceInfo.xml `margeAccountUUID`
  - Data directory structure diagram
  - Reference `examples/` for expected format
- Step 3: Redirect speaker
  - `rw` to make filesystem writable
  - Edit `/opt/Bose/etc/SoundTouchSdkPrivateCfg.xml`
  - Before/after for all 4 URLs
  - Reboot speaker
- Warnings section: port 17000 TAP console, `demo enter` factory mode

**Step 2: Commit**

```bash
git add docs/speaker-setup.md
git commit -m "docs: add speaker setup guide (SSH, data extraction, redirect)"
```

---

### Task 3: Write docs/deployment.md

**Files:**
- Create: `docs/deployment.md`

**Step 1: Write deployment guide**

Content per design doc:
- Docker (simplest): `docker run` command with all env vars and volume
- Docker Compose: full `docker-compose.yml` example
- Kubernetes: example manifests based on our actual deployment (namespace, deployment, service, ingress), with placeholder hostname/volume. Note: customize for your ingress controller (Traefik IngressRoute example shown, adapt for nginx Ingress, etc.)
- Bare metal: Python 3.12, venv, pip install, gunicorn, reference soundcork.service.example
- Environment variables table
- Container image info (ghcr.io/timvw/soundcork:main, multi-arch, GitHub Actions)
- Verification: curl root endpoint, check for `{"Bose":"Can't Brick Us"}`

**Step 2: Commit**

```bash
git add docs/deployment.md
git commit -m "docs: add deployment guide (Docker, Compose, k8s, bare metal)"
```

---

### Task 4: Write docs/architecture.md

**Files:**
- Create: `docs/architecture.md`

**Step 1: Write architecture doc**

Content per design doc:
- The problem: Bose shutting down May 6, 2026 (extended from Feb 18)
- Link to official Bose EOL page and their published API docs PDF
- Four servers table with status as of Feb 2026
- How soundcork replaces them (diagram)
- Local mode (recommended) vs proxy mode
- Why local is recommended (firmware update risk via marge)
- Circuit breaker design
- Data flows: power-on, TuneIn playback, Spotify
- Traffic logging

**Step 2: Commit**

```bash
git add docs/architecture.md
git commit -m "docs: add architecture overview (servers, proxy modes, data flows)"
```

---

### Task 5: Write docs/spotify.md

**Files:**
- Create: `docs/spotify.md`

**Step 1: Write Spotify doc**

Content per design doc:
- Two Spotify systems explained
- Spotify Connect (always works, recommended)
- SoundTouch Spotify integration (broken in app)
- Preset fix: kick-start via Spotify Connect
- Why it works (ZeroConf auth, session in RAM)
- Traffic analysis evidence
- SoundTouch app preset config broken → use Bose CLI

**Step 2: Commit**

```bash
git add docs/spotify.md
git commit -m "docs: add Spotify guide (Connect vs SoundTouch, preset workaround)"
```

---

### Task 6: Rewrite README.md

**Files:**
- Modify: `README.md`

**Step 1: Rewrite README**

Replace current content with new structure per design doc:
- Header with brief description
- What Still Works table
- Quick Start (Docker one-liner)
- What You Need
- Setup Overview (4 steps linking to docs/)
- How It Works (brief, link to architecture.md)
- Bose CLI mention
- Credits (deborahgu prominently)
- License

Keep it ~100 lines. Link to docs/ for everything detailed.

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README with quick start, setup overview, and doc links"
```

---

### Task 7: Write Blog Post

**Files:**
- Create: `/Users/tim.van.wassenhove/src/icteam/timvw.be/content/posts/2026/02/17/keep-your-bose-soundtouch-alive.md`

**Step 1: Write blog post**

Hugo frontmatter:
```yaml
---
title: "Keep Your Bose SoundTouch Speaker Alive After the Shutdown"
date: 2026-02-17
draft: false
tags: ["bose", "soundtouch", "self-hosting", "reverse-engineering", "docker"]
categories: ["self-hosting"]
---
```

~120 lines tutorial format per design doc. Reference https://www.bose.co.uk/en_gb/landing_pages/soundtouch-eol.html for the official shutdown info. Link to soundcork repo for all technical details.

**Step 2: Commit in timvw.be repo**

```bash
cd /Users/tim.van.wassenhove/src/icteam/timvw.be
git add content/posts/2026/02/17/keep-your-bose-soundtouch-alive.md
git commit -m "post: keep your bose soundtouch speaker alive after the shutdown"
```

---

### Task 8: Push soundcork changes

**Step 1: Push all soundcork commits**

```bash
cd /Users/tim.van.wassenhove/src/github/soundcork
gh repo set-default timvw/soundcork
git push
```

**Step 2: Wait for CI build**

```bash
gh run watch
```

---

### Task 9: Open Upstream Issues on deborahgu/soundcork

**Step 1: Open issues**

Open 5 new issues using `gh issue create -R deborahgu/soundcork`:

1. "Add Dockerfile and Docker deployment support" — No containerization exists. We have a working Dockerfile (python:3.12-slim, multi-arch amd64+arm64) and GitHub Actions CI. Happy to contribute.

2. "Add example data files (Presets, Sources, Recents, DeviceInfo)" — New users struggle to understand the expected XML format. We have sanitized examples from a real SoundTouch 20 deployment.

3. "Document SSH access on firmware 27.x (USB stick method)" — The old `remote_services on` TAP command is removed in firmware 27.x. The USB stick method works but has gotchas (macOS junk files, possible need for Ethernet). We have a tested step-by-step guide.

4. "Document Spotify behavior: Connect vs SoundTouch integration" — Two separate Spotify systems cause confusion. Spotify Connect works independently. SoundTouch Spotify presets can be fixed by kick-starting via Spotify Connect. Relates to #159.

5. "Document Bose server status (some APIs already returning 404 before May 6 shutdown)" — As of Feb 2026: marge (streaming.bose.com) alive, bmx (content.api.bose.io) returning 404s, updates (worldwide.bose.com) returning 404s. Useful for the community to know what to expect.

6. "Add Kubernetes deployment example" — Example manifests for k8s deployment with Deployment, Service, Ingress. Tested on a home cluster.

**Step 2: Comment on existing issues**

- Issue #152 ("Add proxy functionality"): Comment that we have a working implementation with circuit breaker, configurable via SOUNDCORK_MODE env var. Offer to PR.
- Issue #159 ("Investigate automatic token setup"): Comment with Spotify Connect findings — it re-authenticates the speaker's embedded Spotify client via ZeroConf, no Bose servers needed.

---

### Task 10: Open Upstream PRs on deborahgu/soundcork

**Prerequisites:** Issues from Task 9 must be created first. PRs reference issue numbers.

**Step 1: Prepare upstream branch**

```bash
cd /Users/tim.van.wassenhove/src/github/soundcork
git remote add upstream https://github.com/deborahgu/soundcork.git  # if not already
git fetch upstream
```

**Step 2: Create PRs (one per logical group)**

PR 1: Dockerfile + Docker deployment
- Dockerfile, .dockerignore, Docker section of deployment docs
- References issue from Task 9 step 1.1

PR 2: Proxy middleware (references issue #152)
- proxy.py, config.py changes, requirements.txt (httpx), SOUNDCORK_MODE docs
- This is the biggest PR — may want to discuss in issue #152 first

PR 3: Example data files
- examples/ directory with all 4 XML files
- References issue from Task 9 step 1.2

PR 4: Documentation
- docs/speaker-setup.md, docs/spotify.md, docs/architecture.md
- References issues from Task 9 steps 1.3, 1.4, 1.5

PR 5: Kubernetes example
- k8s manifests with placeholder values
- References issue from Task 9 step 1.6

**Note:** Per CONTRIBUTING.md, nontrivial changes should start with an issue. Wait for maintainer acknowledgment before opening large PRs (especially PR 2).
