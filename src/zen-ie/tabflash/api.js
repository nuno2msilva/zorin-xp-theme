/* Zorin XP — new tab notice in compact mode.
 *
 * When a tab opens in the background (e.g. a middle click on a link), the
 * window gets the zxp-tab-flash attribute and the tab zxp-flash during the
 * animation; userChrome (src/zen-ie/ie.css) draws the flashing orange strip
 * on the left edge (compact mode: the tab bar is hidden) and the tab
 * flashing like an XP taskbar button (sidebar visible). Done here, and not
 * only in CSS, because the CSS flashed again on startup (restored tabs) and
 * when switching spaces (tabs shown again). */
"use strict";

/* global ExtensionAPI, ChromeUtils, Services */
const { setTimeout, clearTimeout } = ChromeUtils.importESModule("resource://gre/modules/Timer.sys.mjs");
const ATTR = "zxp-tab-flash";
const TAB_ATTR = "zxp-flash";
const FLASH_MS = 1100;

this.zxpTabFlash = class extends ExtensionAPI {
  onStartup() {
    this.windows = new Set();
    this.ready = false;
    // (the tabs restored on startup do not count)
    // (the module moved in Firefox 158: the new one first, the old one after)
    let SessionStore = null;
    for (const url of ["moz-src:///browser/components/sessionstore/SessionStore.sys.mjs",
                       "resource:///modules/sessionstore/SessionStore.sys.mjs"]) {
      try {
        ({ SessionStore } = ChromeUtils.importESModule(url));
        break;
      } catch (e) {}
    }
    if (SessionStore) {
      SessionStore.promiseAllWindowsRestored.then(() => {
        Services.tm.dispatchToMainThread(() => { this.ready = true; });
      });
    } else {
      this.ready = true;
    }

    // (the elements arrive here wrapped: the tab's JS properties — selected,
    // pinned, ownerGlobal — are not visible; the attributes are used)
    this.onTabOpen = (event, win) => {
      const tab = event.target;
      if (!this.ready || tab.hasAttribute("pinned") || tab.hasAttribute("pending")) {
        return;
      }
      // (a new tab in front is already visible: only the background ones)
      win.setTimeout(() => {
        if (tab.isConnected && !tab.hasAttribute("selected") && !tab.hasAttribute("pending")) {
          this.flash(win, tab);
        }
      }, 0);
    };
    this.track = win => {
      if (this.windows.has(win) || !win.gBrowser) {
        return;
      }
      this.windows.add(win);
      win._zxpTabOpen = event => this.onTabOpen(event, win);
      win.addEventListener("TabOpen", win._zxpTabOpen);
      win.addEventListener("unload", () => this.windows.delete(win), { once: true });
    };
    for (const win of Services.wm.getEnumerator("navigator:browser")) {
      this.track(win);
    }
    this.observer = subject => this.track(subject);
    Services.obs.addObserver(this.observer, "browser-delayed-startup-finished");
    // (if the session restore never notifies, after 10 s it counts anyway)
    this.readyTimer = setTimeout(() => { this.ready = true; }, 10000);
  }

  // the window (strip on the edge, compact mode) and the tab itself (sidebar
  // visible) flash together
  flash(win, tab) {
    const root = win.document.documentElement;
    root.removeAttribute(ATTR);
    root.getBoundingClientRect();         // (restarts the animation)
    root.setAttribute(ATTR, "true");
    win.clearTimeout(win._zxpTabFlashTimer);
    win._zxpTabFlashTimer = win.setTimeout(() => root.removeAttribute(ATTR), FLASH_MS);
    tab.setAttribute(TAB_ATTR, "true");
    win.setTimeout(() => tab.removeAttribute(TAB_ATTR), FLASH_MS);
  }

  onShutdown() {
    clearTimeout(this.readyTimer);
    if (this.observer) {
      Services.obs.removeObserver(this.observer, "browser-delayed-startup-finished");
      this.observer = null;
    }
    for (const win of this.windows) {
      win.removeEventListener("TabOpen", win._zxpTabOpen);
      win.document.documentElement.removeAttribute(ATTR);
      for (const t of win.document.querySelectorAll(`[${TAB_ATTR}]`)) {
        t.removeAttribute(TAB_ATTR);
      }
    }
    this.windows.clear();
  }

  getAPI() {
    return { zxpTabFlash: {} };
  }
};
