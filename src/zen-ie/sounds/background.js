// "Iniciar navegação" do XP (Windows XP Start.wav): um clique quando o
// separador à vista começa a abrir uma página — seguir uma ligação, escrever
// um endereço, Retroceder/Avançar, Página inicial, Atualizar. Os de fundo, os
// quadros (anúncios) e as páginas internas (about:) não clicam.
// (o webNavigation não dispara no Zen: usa-se o estado "a carregar" do
// separador, que chega várias vezes por navegação — redirecionamentos — e
// por isso só conta o primeiro em cada 1,5 s; o Zen não toca WAV: vai em OGG)
const click = new Audio(browser.runtime.getURL("start.ogg"));
const QUIET_MS = 1500;
const lastClick = new Map();        // separador -> hora do último clique

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

// a barra de informações (infobar.js): "Pop-up bloqueado" e "Barra de
// informações" do XP SP2, no máximo um a cada 1,5 s
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
