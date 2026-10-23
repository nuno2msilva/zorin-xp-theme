/*
 * Zorin XP — Internet Explorer 6 in Zen: the background shared by every
 * feature (sounds.js and find-background.js come after it).
 *
 * `features` says what is turned on in the Preferences page (options.html);
 * until the first answer everything counts as on, the default. The toolbar
 * buttons are made by experiments/buttons: Search is the Find window
 * (find-background.js), Favorites and History put their page in the
 * Explorer bar, the extension's one side bar (as in IE6, one bar at a time).
 */
const features = {};
browser.zxpSettings.get().then(all => Object.assign(features, all));
browser.zxpSettings.onChanged.addListener((name, value) => {
    features[name] = value;
});

function enabled(name) {
    return features[name] !== false;
}

const BARS = {
    favorites: {panel: "favorites.html", title: "Favoritos"},
    history: {panel: "history.html", title: "Histórico"},
};

browser.zxpButtons.onClicked.addListener(async (button, windowId) => {
    if (button === "find") {
        findButton(windowId);           // (find-background.js)
        return;
    }
    const bar = BARS[button];
    if (!bar || !enabled(button))
        return;
    await browser.sidebarAction.setPanel({windowId, panel: bar.panel});
    await browser.sidebarAction.setTitle({windowId, title: bar.title});
    await browser.zxpButtons.showBar(windowId, button);
});
