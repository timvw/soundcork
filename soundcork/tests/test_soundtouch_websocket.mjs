// Codex: Behavioral tests for offline and reconnect handling.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const listeners = new Map();
const timers = [];
globalThis.window = {
    location: { protocol: "http:" },
    addEventListener(name, callback) {
        listeners.set(name, callback);
    },
};
globalThis.setTimeout = (callback, delay) => {
    timers.push({ callback, delay });
    return timers.length;
};

class FakeWebSocket {
    static instances = [];

    constructor(url, protocol) {
        this.url = url;
        this.protocol = protocol;
        this.listeners = new Map();
        FakeWebSocket.instances.push(this);
    }

    addEventListener(name, callback) {
        this.listeners.set(name, callback);
    }

    close() {
        this.listeners.get("close")?.();
    }
}
globalThis.WebSocket = FakeWebSocket;

const source = await readFile(new URL("../static/js/soundtouch_websocket.js", import.meta.url), "utf8");
const moduleUrl = "data:text/javascript;base64," + Buffer.from(source).toString("base64");
const { connectWebsocket } = await import(moduleUrl);
const handler = { connected() {}, updateNowPlaying() {}, updateVolume() {} };

test("blank speaker addresses are isolated", () => {
    assert.equal(connectWebsocket("speaker", "", "Kitchen", handler), null);
    assert.equal(timers.length, 0);
});

test("closed sockets reconnect with backoff", () => {
    const socket = connectWebsocket("speaker", "192.168.1.42", "Kitchen", handler);
    socket.listeners.get("close")();

    assert.equal(timers.length, 1);
    assert.equal(timers[0].delay, 5000);
});

test("HTTPS pages fail closed instead of retrying mixed content", () => {
    const timerCount = timers.length;
    window.location.protocol = "https:";
    assert.equal(connectWebsocket("speaker", "192.168.1.42", "Kitchen", handler), null);
    assert.equal(timers.length, timerCount);
    window.location.protocol = "http:";
});

test("reconnect attempts are bounded", () => {
    const timerCount = timers.length;
    let socket = connectWebsocket("speaker", "192.168.1.42", "Kitchen", handler);

    for (let attempt = 0; attempt < 8; attempt += 1) {
        socket.listeners.get("close")();
        timers.at(-1).callback();
        socket = FakeWebSocket.instances.at(-1);
    }
    socket.listeners.get("close")();

    assert.equal(timers.length - timerCount, 8);
    assert.equal(timers.at(-1).delay, 60000);
});

test("page shutdown suppresses new connections", () => {
    const instanceCount = FakeWebSocket.instances.length;
    listeners.get("beforeunload")();

    assert.equal(connectWebsocket("speaker", "192.168.1.42", "Kitchen", handler), null);
    assert.equal(FakeWebSocket.instances.length, instanceCount);
});
