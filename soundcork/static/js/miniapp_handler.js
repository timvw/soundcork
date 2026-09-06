// Codex: Keep live updates dependency-free and compatible with LAN HTTP browsers.
import { SoundTouchHandler, loadSpeakers } from "./soundtouch_websocket.js";

export class MiniAppHandler extends SoundTouchHandler {
    connected(speakerId) {
        console.log("connected to " + speakerId);
    }

    updateNowPlaying(speakerId, track, artist, album, imageUrl, status) {
        const info = document.querySelector("#" + CSS.escape(speakerId + "-info") + " .np-info");
        if (info) {
            info.textContent = track + " - " + artist;
        }

        const sidebar = document.getElementById("sidebar-" + speakerId);
        if (sidebar) {
            const nowPlaying = sidebar.querySelector("span.now_playing");
            const image = sidebar.querySelector("img");
            if (nowPlaying) {
                nowPlaying.textContent = track;
            }
            if (image) {
                image.src = imageUrl;
                image.hidden = !imageUrl;
            }
        }
    }

    updateVolume(speakerId, actualVolume, targetVolume) {
        const volume = document.querySelector("#" + CSS.escape(speakerId + "-info") + " .volume");
        if (volume) {
            volume.textContent = "Volume: " + actualVolume;
        }

        const sidebar = document.getElementById("sidebar-" + speakerId);
        const slider = sidebar ? sidebar.querySelector("input.slider") : null;
        if (slider) {
            slider.value = actualVolume;
        }
    }
}

const accountId = document.body.dataset.accountId;
if (accountId) {
    loadSpeakers(accountId, new MiniAppHandler());
}
