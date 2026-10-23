/* Zorin XP — the "Save As" folder remembered per site, not globally.
 *
 * Zen (DownloadLastDir) stores the folder where something was saved twice:
 * per site (content-prefs, per domain) and in a global preference,
 * browser.download.lastDir, which is the fallback for sites where nothing
 * was saved yet. Deleting the global one right after every save leaves only
 * the per-site memory; on a new site Zen suggests the downloads folder
 * (Downloads.getPreferredDownloadsDirectory), which is where the dialog
 * opens. Private windows use a session-only memory and do not change. */
"use strict";

/* global ExtensionAPI, Services */
const PREF = "browser.download.lastDir";

this.zxpLastDir = class extends ExtensionAPI {
  onStartup() {
    this.clear = () => {
      // (after Zen has finished saving: the site's one is written before)
      Services.tm.dispatchToMainThread(() => {
        if (Services.prefs.prefHasUserValue(PREF)) {
          Services.prefs.clearUserPref(PREF);
        }
      });
    };
    Services.prefs.addObserver(PREF, this.clear);
    this.clear();
  }

  onShutdown() {
    if (this.clear) {
      Services.prefs.removeObserver(PREF, this.clear);
      this.clear = null;
    }
  }

  getAPI() {
    return { zxpLastDir: {} };
  }
};
