/* Zorin XP — Internet Explorer title and icon.
 *
 * Zen writes the window title as "page — Zen Browser"; here each window's
 * gBrowser gives XP's IE6 title instead ("Google - Microsoft Internet
 * Explorer", as in the capture; without a page, just "Microsoft Internet
 * Explorer"). That title is what shows in the title bar and on the taskbar
 * button.
 *
 * The icon of both is drawn by GNOME Shell (zorin-xp extension,
 * zenIcons.js), which does not know which page is open: for each window, the
 * selected page's favicon goes, as a 16 px PNG, to a cache folder (in the
 * Flatpak, ~/.var/app/app.zen_browser.zen/cache/zorin-xp-favicons), with an
 * index.json "window title -> file". Without a favicon (or an empty tab),
 * IE's page (the theme's img/page.png). */
"use strict";

/* global ExtensionAPI, Services, ChromeUtils, IOUtils, PathUtils, Ci */
const BRAND = "Microsoft Internet Explorer";
const HTML = "http://www.w3.org/1999/xhtml";
const SIZE = 16;
const DEFAULT = "page.png";

function cacheDir() {
  // (the test Zen, tools/test/zentest, uses another folder: it is the same Flatpak)
  const test = Services.env.get("ZXP_FAVICON_DIR");
  if (test) {
    return test;
  }
  const xdg = Services.env.get("XDG_CACHE_HOME");
  const base = xdg || PathUtils.join(Services.dirsvc.get("Home", Ci.nsIFile).path, ".cache");
  return PathUtils.join(base, "zorin-xp-favicons");
}

// (short, stable name for each icon address: 32-bit FNV-1a)
function hash(text) {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h.toString(16).padStart(8, "0");
}

this.zxpTitle = class extends ExtensionAPI {
  onStartup() {
    this.dir = cacheDir();
    this.index = PathUtils.join(this.dir, "index.json");
    this.files = new Set();         // icons already written (in this session)
    this.windows = new Map();       // window -> {restore, icon, timer}
    // (the folder starts empty on every start: only the icons in use stay)
    this.ready = (async () => {
      await IOUtils.remove(this.dir, { recursive: true, ignoreAbsent: true });
      await IOUtils.makeDirectory(this.dir, { createAncestors: true });
      const page = PathUtils.join(PathUtils.profileDir, "chrome", "zorin-xp-ie", "img", "page.png");
      if (await IOUtils.exists(page)) {
        await IOUtils.copy(page, PathUtils.join(this.dir, DEFAULT));
        this.files.add(DEFAULT);
      }
    })().catch(e => console.warn("Zorin XP: pasta dos ícones:", e));

    this.track = win => {
      if (this.windows.has(win) || !win.gBrowser) {
        return;
      }
      // (without the wrapper: the original method uses gBrowser's private
      // fields, which only work on the real object)
      const gb = win.wrappedJSObject.gBrowser;
      const own = Object.hasOwn(gb, "getWindowTitleForBrowser");
      const orig = gb.getWindowTitleForBrowser;
      const state = { icon: DEFAULT, timer: 0 };
      gb.getWindowTitleForBrowser = (browser) => {
        const title = orig.call(gb, browser);
        // (Zen joins "page — brand": only the page stays)
        const i = title.lastIndexOf(" — ");
        const page = i >= 0 ? title.slice(0, i) : "";
        this.schedule(win);
        return page ? `${page} - ${BRAND}` : BRAND;
      };
      const tabs = win.gBrowser.tabContainer;
      const onTab = () => this.schedule(win);
      tabs.addEventListener("TabSelect", onTab);
      tabs.addEventListener("TabAttrModified", onTab);
      state.restore = () => {
        tabs.removeEventListener("TabSelect", onTab);
        tabs.removeEventListener("TabAttrModified", onTab);
        win.clearTimeout(state.timer);
        if (own) {
          gb.getWindowTitleForBrowser = orig;
        } else {
          delete gb.getWindowTitleForBrowser;
        }
        gb.updateTitlebar();
      };
      this.windows.set(win, state);
      gb.updateTitlebar();
      win.addEventListener("unload", () => {
        this.windows.delete(win);
        this.writeIndex();
      }, { once: true });
    };
    for (const win of Services.wm.getEnumerator("navigator:browser")) {
      this.track(win);
    }
    this.observer = subject => this.track(subject);
    Services.obs.addObserver(this.observer, "browser-delayed-startup-finished");
  }

  // (several notices in a row when switching tabs or loading a page:
  // a single update)
  schedule(win) {
    const state = this.windows.get(win);
    if (!state || state.timer) {
      return;
    }
    state.timer = win.setTimeout(() => {
      state.timer = 0;
      this.updateWindow(win).catch(e => console.warn("Zorin XP: ícone da janela:", e));
    }, 150);
  }

  async updateWindow(win) {
    await this.ready;
    const state = this.windows.get(win);
    if (!state || win.closed) {
      return;
    }
    const tab = win.gBrowser.selectedTab;
    const url = tab && !tab.hasAttribute("zen-empty-tab") ? tab.getAttribute("image") : "";
    state.icon = url ? (await this.iconFile(win, url)) || DEFAULT : DEFAULT;
    await this.writeIndex();
  }

  // the favicon as a 16 px PNG (drawn on a canvas of the window itself, which
  // knows how to open Firefox's icon addresses: page-icon:, data:...)
  async iconFile(win, url) {
    const name = `${hash(url)}.png`;
    if (this.files.has(name)) {
      return name;
    }
    try {
      const doc = win.document;
      const img = doc.createElementNS(HTML, "img");
      img.src = url;
      await img.decode();
      const canvas = doc.createElementNS(HTML, "canvas");
      canvas.width = SIZE;
      canvas.height = SIZE;
      canvas.getContext("2d").drawImage(img, 0, 0, SIZE, SIZE);
      const b64 = canvas.toDataURL("image/png").split(",")[1];
      const bytes = new Uint8Array(ChromeUtils.base64URLDecode(
        b64.replace(/\+/g, "-").replace(/\//g, "_"), { padding: "ignore" }));
      await IOUtils.write(PathUtils.join(this.dir, name), bytes);
      this.files.add(name);
      return name;
    } catch (e) {
      return null;
    }
  }

  async writeIndex() {
    const map = {};
    for (const [win, state] of this.windows) {
      if (!win.closed) {
        map[win.document.title] = state.icon;
      }
    }
    try {
      await IOUtils.writeJSON(this.index, map, { tmpPath: `${this.index}.tmp` });
    } catch (e) {}
  }

  onShutdown() {
    if (this.observer) {
      Services.obs.removeObserver(this.observer, "browser-delayed-startup-finished");
      this.observer = null;
    }
    for (const state of this.windows.values()) {
      state.restore();
    }
    this.windows.clear();
    // (without the extension, the windows go back to the application's icon)
    IOUtils.remove(this.index, { ignoreAbsent: true }).catch(() => {});
  }

  getAPI() {
    return { zxpTitle: {} };
  }
};
