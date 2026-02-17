"""Spotify ZeroConf primer for SoundTouch speakers.

After Bose's cloud servers shut down, speakers can no longer obtain
Spotify credentials via the marge /full account response.  Instead,
we prime speakers by sending a valid Spotify access token directly
to their ZeroConf endpoint (port 8200) using the addUser action.

This is the same mechanism the Spotify desktop app uses: a plain
access token is sent as the blob parameter (no DH encryption).

The primer runs:
  - Once on speaker boot (triggered by the power_on endpoint)
  - Periodically (every ~45 minutes) to keep the session alive
    before the access token expires (1 hour lifetime)

Configuration:
  - SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set
  - A Spotify account must be linked via the management API
  - Speaker IP addresses are read from the datastore (DeviceInfo)
"""

import logging
import threading
import time
import urllib.parse
import urllib.request

from soundcork.config import Settings
from soundcork.datastore import DataStore
from soundcork.spotify_service import SpotifyService

logger = logging.getLogger(__name__)

ZEROCONF_PORT = 8200
REPRIME_INTERVAL_SECONDS = 45 * 60  # 45 minutes


class ZeroConfPrimer:
    def __init__(
        self,
        spotify: SpotifyService,
        datastore: DataStore,
        settings: Settings,
    ):
        self._spotify = spotify
        self._datastore = datastore
        self._settings = settings
        self._timer: threading.Timer | None = None

    def prime_speaker(self, speaker_ip: str) -> bool:
        """Send addUser to a speaker's ZeroConf endpoint.

        Returns True if the speaker accepted and set activeUser.
        """
        token = self._spotify.get_fresh_token_sync()
        if not token:
            logger.warning("No Spotify token available — cannot prime %s", speaker_ip)
            return False

        user_id = self._spotify.get_spotify_user_id()
        if not user_id:
            logger.warning("No Spotify user ID — cannot prime %s", speaker_ip)
            return False

        try:
            result = self._send_add_user(speaker_ip, user_id, token)
            status = result.get("status", -1)
            if status != 101:
                logger.warning(
                    "addUser to %s returned status %s: %s",
                    speaker_ip,
                    status,
                    result.get("statusString", ""),
                )
                return False

            logger.info("addUser accepted by %s (status 101)", speaker_ip)

            # Verify activeUser was actually set
            time.sleep(2)
            active_user = self._get_active_user(speaker_ip)
            if active_user:
                logger.info(
                    "Speaker %s primed for Spotify (activeUser=%s)",
                    speaker_ip,
                    active_user,
                )
                return True
            else:
                logger.warning(
                    "Speaker %s returned 101 but activeUser is still empty",
                    speaker_ip,
                )
                return False

        except Exception:
            logger.exception("Failed to prime speaker %s", speaker_ip)
            return False

    def prime_all_speakers(self):
        """Prime all known speakers."""
        if not self._settings.spotify_client_id:
            logger.debug("Spotify not configured — skipping primer")
            return

        speakers = self._discover_speaker_ips()
        if not speakers:
            logger.info("No speakers found to prime")
            return

        for ip in speakers:
            self.prime_speaker(ip)

    def start_periodic(self):
        """Start the periodic re-prime background task."""
        if not self._settings.spotify_client_id:
            logger.info("Spotify not configured — periodic primer disabled")
            return

        self._schedule_next()
        logger.info(
            "Periodic Spotify primer started (every %d minutes)",
            REPRIME_INTERVAL_SECONDS // 60,
        )

    def stop_periodic(self):
        """Stop the periodic re-prime background task."""
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule_next(self):
        """Schedule the next re-prime."""
        self._timer = threading.Timer(REPRIME_INTERVAL_SECONDS, self._periodic_tick)
        self._timer.daemon = True
        self._timer.start()

    def _periodic_tick(self):
        """Called by the timer — prime all speakers and reschedule."""
        try:
            logger.info("Periodic Spotify re-prime running...")
            self.prime_all_speakers()
        except Exception:
            logger.exception("Error during periodic Spotify re-prime")
        finally:
            self._schedule_next()

    def _discover_speaker_ips(self) -> list[str]:
        """Get IP addresses of all known speakers from the datastore."""
        ips = []
        try:
            # Walk the data directory to find all accounts and devices
            import os

            data_dir = self._settings.data_dir
            if not data_dir or not os.path.isdir(data_dir):
                return ips

            for account_id in os.listdir(data_dir):
                account_path = os.path.join(data_dir, account_id)
                if not os.path.isdir(account_path):
                    continue

                try:
                    device_ids = self._datastore.list_devices(account_id)
                except (StopIteration, FileNotFoundError):
                    continue

                for device_id in device_ids:
                    if not device_id:
                        continue
                    try:
                        info = self._datastore.get_device_info(account_id, device_id)
                        if info.ip_address:
                            ips.append(info.ip_address)
                    except Exception:
                        logger.debug(
                            "Could not read device info for %s/%s",
                            account_id,
                            device_id,
                        )
        except Exception:
            logger.exception("Error discovering speaker IPs")

        return ips

    @staticmethod
    def _send_add_user(speaker_ip: str, user_id: str, token: str) -> dict:
        """Send addUser to the speaker's ZeroConf endpoint."""
        import json

        post_data = urllib.parse.urlencode(
            {
                "action": "addUser",
                "userName": user_id,
                "blob": token,
                "clientKey": "",
                "tokenType": "accesstoken",
            }
        ).encode()

        url = f"http://{speaker_ip}:{ZEROCONF_PORT}/zc"
        req = urllib.request.Request(
            url,
            data=post_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())

    @staticmethod
    def _get_active_user(speaker_ip: str) -> str:
        """Check the speaker's activeUser via ZeroConf getInfo."""
        import json

        url = f"http://{speaker_ip}:{ZEROCONF_PORT}/zc?action=getInfo"
        with urllib.request.urlopen(url, timeout=5) as resp:
            info = json.loads(resp.read())
        return info.get("activeUser", "")
