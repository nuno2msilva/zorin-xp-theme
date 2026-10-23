// XP's "Iniciar navegação" (Start Navigation, Windows XP Start.wav): a click
// when the visible tab starts opening a page — following a link, typing an
// address, Back/Forward, Home, Refresh. Background tabs, frames (ads) and
// internal pages (about:) do not click.
// (webNavigation does not fire in Zen: the tab's "loading" state is used,
// which arrives several times per navigation — redirects — so only the
// first one every 1.5 s counts; Zen does not play WAV: it goes as OGG)
const click = new Audio(browser.runtime.getURL("start.ogg"));
const QUIET_MS = 1500;
const lastClick = new Map();        // tab -> time of the last click

function play() {
    click.currentTime = 0;
    click.play().catch(() => {});
}

browser.tabs.onUpdated.addListener((tabId, info, tab) => {
    if (info.status !== "loading" || !tab.active || !/^(https?|ftp|file):/.test(tab.url))
        return;
    const now = Date.now();
    if (now - (lastClick.get(tabId) || 0) < QUIET_MS)
        return;
    lastClick.set(tabId, now);
    play();
}, {properties: ["status"]});

browser.tabs.onRemoved.addListener(tabId => lastClick.delete(tabId));

// the information bar (infobar.js): XP SP2's "Pop-up bloqueado" and
// "Barra de informações", at most one every 1.5 s
const infobar = {
    "popup-blocked": new Audio(browser.runtime.getURL("popup-blocked.ogg")),
    "infobar": new Audio(browser.runtime.getURL("infobar.ogg")),
};
let lastInfobar = 0;
browser.runtime.onMessage.addListener(msg => {
    const sound = infobar[msg.op];
    const now = Date.now();
    if (!sound || now - lastInfobar < QUIET_MS)
        return;
    lastInfobar = now;
    sound.currentTime = 0;
    sound.play().catch(() => {});
});
