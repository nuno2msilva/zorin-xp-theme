/*
 * "Procurar" (Search) and Ctrl+F: the Find window (a separate window, which
 * can be moved, as in IE). It searches the active tab of the window it was
 * called from, with the browser's own find (without touching the page).
 *
 * Opening a browser window takes its time, so the window is kept ready:
 * after the first time, closing it (Cancel, Esc, Search) only minimizes it,
 * and calling it again just restores it. It lives in a private window, which
 * does not count for Zen's session (which is only saved when the last
 * "regular" window closes), and it closes when there are no normal windows
 * left. The GNOME extension takes it off the taskbar and Alt+Tab. Without the
 * private windows permission, the window really closes, as before.
 */
const WIDTH = 384, HEIGHT = 152;
let find = null;          // {id, parent, keep}
let opening = null;

function placement(parent) {
    return {
        left: Math.round(parent.left + (parent.width - WIDTH) / 2),
        top: Math.round(parent.top + (parent.height - HEIGHT) / 3),
    };
}

// (in Zen the click may arrive without the tab: the last focused window)
async function parentOf(tab) {
    if (tab && (!find || tab.windowId !== find.id))
        return browser.windows.get(tab.windowId);
    if (find && find.parent)
        return browser.windows.get(find.parent).catch(() => browser.windows.getLastFocused({windowTypes: ["normal"]}));
    return browser.windows.getLastFocused({windowTypes: ["normal"]});
}

async function visible() {
    if (!find)
        return false;
    const w = await browser.windows.get(find.id).catch(() => null);
    return !!w && w.state !== "minimized";
}

async function show(parent) {
    if (find) {
        find.parent = parent.id;
        await browser.windows.update(find.id, {state: "normal", focused: true, ...placement(parent)});
        browser.runtime.sendMessage({op: "shown"}).catch(() => {});
        return;
    }
    const keep = await browser.extension.isAllowedIncognitoAccess();
    const win = await browser.windows.create({
        url: "find.html",
        type: "popup",
        incognito: keep,
        width: WIDTH,
        height: HEIGHT,
        ...placement(parent),
    });
    find = {id: win.id, parent: parent.id, keep};
}

async function hide() {
    if (!find)
        return;
    if (find.keep) {
        await browser.windows.update(find.id, {state: "minimized"});
        if (find.parent)
            browser.windows.update(find.parent, {focused: true}).catch(() => {});
    } else {
        const id = find.id;
        find = null;
        await browser.windows.remove(id).catch(() => {});
    }
}

// one request at a time (two clicks in a row do not open two windows)
function serial(fn) {
    return (...args) => {
        opening = (opening || Promise.resolve()).then(() => fn(...args)).catch(e => console.error("Localizar:", e));
        return opening;
    };
}

// the Search button opens and closes
browser.browserAction.onClicked.addListener(serial(async tab => {
    if (await visible())
        await hide();
    else
        await show(await parentOf(tab));
}));

// Ctrl+F opens, or brings to the front the one already open
browser.commands.onCommand.addListener(serial(async (command, tab) => {
    if (command !== "localizar")
        return;
    if (await visible() && tab && tab.windowId === find.id) {
        browser.runtime.sendMessage({op: "shown"}).catch(() => {});
        return;
    }
    await show(await parentOf(tab));
}));

// the Find page asks where to search, and asks to hide itself
browser.runtime.onMessage.addListener(msg => {
    if (msg.op === "parent")
        return Promise.resolve(find ? find.parent : null);
    if (msg.op === "hide")
        return serial(hide)();
});

browser.windows.onRemoved.addListener(async id => {
    if (!find)
        return;
    if (id === find.id) {
        find = null;
        return;
    }
    // (without normal windows, the ready window must not keep the browser open)
    const normal = await browser.windows.getAll({windowTypes: ["normal"]});
    if (!normal.length) {
        const fid = find.id;
        find = null;
        browser.windows.remove(fid).catch(() => {});
    } else if (id === find.parent) {
        // (as in IE: the Find window goes with its window)
        find.parent = null;
        serial(hide)();
    }
});
