# Spotify on SoundTouch

## Two Different Spotify Systems

There are two completely separate ways Spotify works on a SoundTouch speaker. This is a common source of confusion.

### 1. Spotify Connect (Always Works)

- The speaker advertises itself as a Spotify Connect device on your local network
- Open the Spotify app on your phone or computer, tap the speaker/device icon, and select your SoundTouch speaker
- Audio streams directly from Spotify's CDN to the speaker
- **No Bose servers involved** — purely between the Spotify app, Spotify's servers, and the speaker
- **No soundcork involvement** — Spotify Connect operates independently

### 2. SoundTouch Spotify Integration (Presets)

- This is what the SoundTouch app used for setting Spotify presets (buttons 1-6)
- Originally relied on Bose's OAuth token management via the marge server
- After the Bose shutdown, this path is broken **unless soundcork handles the token refresh**

## Automatic Spotify Support

Soundcork can keep Spotify presets working automatically. There are two mechanisms that serve different purposes, and both run together:

### ZeroConf Primer (Cold Boot Activation)

On cold boot, the speaker does **not** request a Spotify token — it only fetches account data, source providers, and streaming tokens. Without an active Spotify session, presets fail silently.

The ZeroConf primer solves this by proactively pushing a fresh Spotify access token to the speaker via the ZeroConf endpoint (port 8200). This is the same mechanism the Spotify desktop app uses when you cast to a speaker.

There are two ways to run the ZeroConf primer:

**Server-side** (default): SoundCork pushes tokens to the speaker over the
network. No installation on the speaker needed.

- On speaker boot (`power_on` event), with retry/backoff (5s, 10s, 20s delays)
- Periodically every 45 minutes (tokens expire after 1 hour)
- When a new speaker is first seen via marge requests

**On-speaker**: A boot script on the speaker itself fetches a token from
SoundCork and primes locally. See the
[Speaker Setup Guide](speaker-setup.md#step-5-install-spotify-boot-primer-optional)
for installation instructions.

**Boot sequence observed:**
```
power_on → bmx/services → media icons → sourceproviders → /full → streaming_token → provider_settings
```
No OAuth token request happens during boot — the ZeroConf primer is what activates Spotify.

### OAuth Token Intercept (Ongoing Refresh)

Once the speaker has an active Spotify session (from the ZeroConf primer or a previous Spotify Connect cast), it will periodically refresh its token by calling an OAuth endpoint. Soundcork intercepts these requests and returns a valid token.

**How it works:**
1. Speaker sends `POST /oauth/device/{deviceId}/music/musicprovider/15/token/cs3`
2. Soundcork refreshes the token using the stored Spotify account credentials
3. Returns a fresh access token as JSON
4. The speaker uses this token for continued Spotify playback

This is transparent — the speaker manages its own refresh cycle, just like it did with `streamingoauth.bose.com`. The speaker sends these requests to the marge server, but to a hostname it derives from `margeServerUrl` by inserting `oauth` before the first dot of the host (`streaming.bose.com` → `streamingoauth.bose.com`).

<!-- Claude: Document the derived OAuth host and the IP-address pitfall. -->
**If `margeServerUrl` is an IP address**, the derived host can't be resolved: `http://192.168.1.10:8000` becomes `http://192oauth.168.1.10:8000`. The token request fails with a DNS error (`URL Fetch (...) failed with CURL ErrorCode 6` in the speaker log). The most visible symptom shows up when the speaker's Spotify shuffle is on: playlist and album presets hang in `BUFFERING`, because the speaker needs this token to pick a random start track (`PlayRandomIndexForUri`). Single-track presets and non-shuffled playlists still play. To fix it, either:

- use a hostname for `margeServerUrl` and make both names resolve to soundcork (e.g. `soundcork.lan` and `soundcorkoauth.lan`), or
- map the derived name on the speaker at boot, in `/mnt/nv/rc.local`. The root filesystem stays read-only and the mapping is reapplied on every boot:

  ```sh
  if ! grep -q "192oauth.168.1.10" /etc/hosts; then
      cp /etc/hosts /tmp/hosts && echo "192.168.1.10	192oauth.168.1.10" >> /tmp/hosts && mount -o bind /tmp/hosts /etc/hosts
  fi
  ```

## Setup

### Step 1: Register a Spotify App

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
   - **Redirect URI**: `{your-soundcork-url}/mgmt/spotify/callback` (e.g., `https://soundcork.local:8000/mgmt/spotify/callback`)
   - **APIs used**: Web API
3. Note the **Client ID** and **Client Secret**

### Step 2: Configure Soundcork

Set the environment variables:

```bash
SPOTIFY_CLIENT_ID=your-client-id
SPOTIFY_CLIENT_SECRET=your-client-secret
```

### Step 3: Link Your Spotify Account

The redirect URI used in the flow must exactly match one registered in your Spotify app. Spotify only accepts HTTPS redirect URIs, except loopback addresses (`http://127.0.0.1:PORT/...`; `localhost` is not accepted).

**In a browser:** open `https://your-soundcork/mgmt/spotify/init` (this is what the Web UI does). It redirects to Spotify with `{BASE_URL}/mgmt/spotify/callback` as the redirect URI and completes the flow on the server, so that URI must be registered and reachable from your browser.

**With the management API**, using `SPOTIFY_REDIRECT_URI` as the redirect URI:

```bash
# Start the OAuth flow — returns {"redirectUrl": "..."}
curl -u admin:password -X POST https://your-soundcork/mgmt/spotify/init

# Open redirectUrl in a browser and authorize. Spotify redirects to
# SPOTIFY_REDIRECT_URI?code=AUTH_CODE — copy the code from the address bar
# (the page itself doesn't need to load), then:
curl -u admin:password -X POST "https://your-soundcork/mgmt/spotify/confirm?code=AUTH_CODE"

# Verify the account is linked
curl -u admin:password https://your-soundcork/mgmt/spotify/accounts
```

Or use the [companion app](https://github.com/timvw/ueberboese-app) which handles this flow automatically.

Linking again replaces the stored tokens for the same Spotify user.

### Step 4: Verify

After linking your Spotify account:
- The OAuth intercept works immediately — the speaker will get fresh tokens on its next refresh cycle
- The ZeroConf primer (if enabled) will prime the speaker within a few minutes
- Press a Spotify preset button on the speaker — it should play

## Technical Details

### Token Lifecycle

- Spotify access tokens expire after **1 hour** (3600 seconds)
- The speaker's firmware requests a new token via the OAuth endpoint before expiry
- The ZeroConf primer re-primes every **45 minutes** as an additional safety net
- Soundcork caches tokens to avoid unnecessary Spotify API calls
- Refresh tokens expire too. The Spotify dashboard shows each app's **Refresh Token Lifetime** (for example 180 days). When it runs out, soundcork logs `Spotify token refresh failed: {"error":"invalid_grant","error_description":"Refresh token revoked"}`, `/mgmt/spotify/token` returns 503, and speakers lose Spotify presets after their next reboot. Link the account again ([Step 3](#step-3-link-your-spotify-account)).
- Spotify allows one stream per account. If several speakers use the same Spotify account, starting playback on one stops the other after a few seconds.

### What `cs3` / `token_version_3` Means

The speaker requests tokens with `tokenType=cs3` in the URL. This corresponds to `token_version_3` in the XML credential format — it's Bose's internal versioning for their OAuth credential schema. The actual value is a standard Spotify access token.

### Speaker ZeroConf Endpoint

Each speaker exposes a ZeroConf endpoint on port 8200:
- `GET /zc?action=getInfo` — returns speaker info including `activeUser`, `libraryVersion`
- `POST /zc` with `action=addUser` — sets the active Spotify user

### Alternative Approach: Manual Kick-Start

If you don't want to configure Spotify credentials in soundcork, you can manually prime the speaker by casting one song via the Spotify app (Spotify Connect). This gives the speaker a temporary in-memory session that enables presets. However, you'll need to repeat this after every speaker reboot.

## Managing Presets

The official SoundTouch app can no longer configure presets after the cloud
shutdown. There are two ways to manage presets:

### Web UI

The SoundCork Web UI (`/webui/`) lets you manage all 6 presets visually. You
can set presets from three source types:

- **Spotify** — paste a Spotify URI or URL (playlist, album, artist, track),
  select your linked Spotify account, and save. The UI previews the entity
  (artwork + name) before saving.
- **TuneIn** — search for radio stations by name, preview station details
  (logo, description, genre, location), and save.
- **Internet Radio** — enter a stream URL manually with an optional station
  name and cover art URL. Use this for stations not in TuneIn's directory.

### Bose CLI

The [Bose CLI](https://github.com/timvw/bose) manages presets directly via the
speaker's local API (port 8090):

```bash
brew install timvw/tap/bose
bose preset       # view presets
bose preset 1     # get a specific preset
bose status       # speaker status
```
