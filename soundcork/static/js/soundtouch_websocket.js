// Codex: Isolate failures per speaker and reconnect transient websocket drops.
const RECONNECT_DELAY_MS = 5000;
let pageClosing = false;

window.addEventListener("beforeunload", () => {
    pageClosing = true;
}, { once: true });

export class SoundTouchHandler {
    connected(speakerId) {
    }
    updateNowPlaying(speakerId, track, artist, album, imageUrl, status) {
    }
    updateVolume(speakerId, actualVolume, targetVolume) {
    }
}

export async function loadSpeakers(accountId, handler) {
    try {
        const response = await fetch("/marge/streaming/account/" + encodeURIComponent(accountId) + "/devices", {
            credentials: "same-origin",
        });
        if (!response.ok) {
            throw new Error("speaker request failed: " + response.status);
        }
        const xml = new DOMParser().parseFromString(await response.text(), "application/xml");
        if (xml.querySelector("parsererror")) {
            throw new Error("speaker response was not valid XML");
        }

        for (const device of xml.getElementsByTagName("device")) {
            const deviceId = device.getAttribute("deviceid");
            const ipAddr = device.getElementsByTagName("ipaddress")[0]?.textContent?.trim();
            const name = device.getElementsByTagName("name")[0]?.textContent || "";
            if (!deviceId || !ipAddr) {
                console.warn("Skipping speaker without device ID or IP address", name);
                continue;
            }
            connectWebsocket(deviceId, ipAddr, name, handler);
        }
    } catch (error) {
        console.error("Could not load speakers", error);
    }
}

export function connectWebsocket(speakerId, ipAddr, name, handler) {
    if (!ipAddr || pageClosing) {
        return null;
    }

    let websocket;
    try {
        websocket = new WebSocket("ws://" + ipAddr + ":8080", "gabbo");
    } catch (error) {
        console.error("Could not connect websocket for " + name, error);
        scheduleReconnect(speakerId, ipAddr, name, handler);
        return null;
    }

    websocket.addEventListener("open", () => {
        handler.connected(speakerId);
    });
    websocket.addEventListener("message", (event) => {
        try {
            const xmlDoc = new DOMParser().parseFromString(event.data, "application/xml");
            if (xmlDoc.querySelector("parsererror")) {
                throw new Error("invalid websocket XML");
            }
            const updates = xmlDoc.getElementsByTagName("updates")[0];
            if (!updates || updates.getAttribute("deviceID") !== speakerId) {
                return;
            }

            const nowPlaying = updates.getElementsByTagName("nowPlaying")[0];
            if (nowPlaying) {
                parseNowPlayingMessage(nowPlaying, speakerId, handler);
                return;
            }
            const volume = updates.getElementsByTagName("volumeUpdated")[0];
            if (volume) {
                parseVolumeMessage(volume, speakerId, handler);
            }
        } catch (error) {
            console.warn("Ignoring malformed websocket message from " + name, error);
        }
    });
    websocket.addEventListener("error", () => {
        websocket.close();
    });
    websocket.addEventListener("close", () => {
        scheduleReconnect(speakerId, ipAddr, name, handler);
    });
    return websocket;
}

function scheduleReconnect(speakerId, ipAddr, name, handler) {
    if (!pageClosing) {
        setTimeout(() => connectWebsocket(speakerId, ipAddr, name, handler), RECONNECT_DELAY_MS);
    }
}

function elementText(parent, tagName) {
    return parent.getElementsByTagName(tagName)[0]?.textContent || "";
}

function parseNowPlayingMessage(nowPlaying, speakerId, handler) {
    handler.updateNowPlaying(
        speakerId,
        elementText(nowPlaying, "track"),
        elementText(nowPlaying, "artist"),
        elementText(nowPlaying, "album"),
        elementText(nowPlaying, "art"),
        elementText(nowPlaying, "playStatus"),
    );
}

function parseVolumeMessage(volume, speakerId, handler) {
    handler.updateVolume(
        speakerId,
        elementText(volume, "actualvolume"),
        elementText(volume, "targetvolume"),
    );
}
